from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import PaymentOrder, SubscriptionPackage, User, UserSubscription
from app.schemas.common import AuthUser, PaymentCallbackRequest, PaymentOrderCreateRequest, PaymentRefundApplyRequest, PaymentRefundStatsRequest
from app.services.wechat_pay_service import wechat_pay_service


REFUND_STATUS = "refunded"


def _get_user(db: Session, current_user: AuthUser) -> User:
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _get_package_or_404(db: Session, package_code: str) -> SubscriptionPackage:
    package = db.query(SubscriptionPackage).filter(
        SubscriptionPackage.package_code == package_code,
        SubscriptionPackage.is_active.is_(True),
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="套餐不存在或不可用")
    return package


def _serialize_order(order: PaymentOrder) -> dict:
    return {
        "orderNo": order.order_no,
        "status": order.status,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "amount": float(order.amount or 0),
        "payChannel": order.pay_channel,
        "thirdPartyOrderNo": order.third_party_order_no or "",
        "paidAt": order.paid_at.isoformat() if order.paid_at else "",
        "createdAt": order.created_at.isoformat() if order.created_at else "",
    }


def _serialize_payment_response(order: PaymentOrder, package: SubscriptionPackage, pay_payload: dict | None = None) -> dict:
    return {
        **_serialize_order(order),
        "packageName": package.package_name,
        "payParams": pay_payload or {},
    }


def _assert_admin(current_user: AuthUser) -> None:
    if not current_user.isAdmin and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _minutes_to_hours(minutes: int) -> int:
    return max((int(minutes or 0) + 59) // 60, 0)


def _get_subscription_for_order(db: Session, order: PaymentOrder) -> UserSubscription | None:
    return db.query(UserSubscription).filter(
        UserSubscription.source_order_no == order.order_no,
        UserSubscription.username == order.username,
    ).first()


def _build_refund_balance(order: PaymentOrder, subscription: UserSubscription | None) -> dict:
    total_minutes = int(subscription.total_minutes or 0) if subscription else 0
    used_minutes = int(subscription.used_minutes or 0) if subscription else 0
    refundable_minutes = max(total_minutes - used_minutes, 0)
    total_hours = _minutes_to_hours(total_minutes)
    used_hours = _minutes_to_hours(used_minutes)
    refundable_hours = _minutes_to_hours(refundable_minutes)
    hourly_amount = round(float(order.amount or 0) / total_hours, 2) if total_hours > 0 else 0
    refundable_amount = round(hourly_amount * refundable_hours, 2)
    refund_payload = order.extra_payload if isinstance(order.extra_payload, dict) else {}
    return {
        **_serialize_order(order),
        "username": order.username,
        "packageCode": order.package_code,
        "packageType": order.package_type,
        "totalMinutes": total_minutes,
        "usedMinutes": used_minutes,
        "refundableMinutes": refundable_minutes,
        "totalHours": total_hours,
        "usedHours": used_hours,
        "refundableHours": refundable_hours,
        "hourlyAmount": hourly_amount,
        "refundableAmount": refundable_amount,
        "refundStatus": order.status,
        "refundInfo": refund_payload.get("refund", {}),
    }


def create_payment_order(db: Session, current_user: AuthUser, data: PaymentOrderCreateRequest) -> dict:
    _get_user(db, current_user)
    package = _get_package_or_404(db, data.packageCode)
    order = PaymentOrder(
        order_no=f"PAY{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}",
        username=current_user.username,
        package_code=package.package_code,
        package_type=package.package_type,
        amount=Decimal(str(package.price or 0)),
        pay_channel=data.payChannel,
        status="pending",
        extra_payload={
            "packageName": package.package_name,
            "scene": data.scene,
            "openId": data.openId or "",
            "clientIp": data.clientIp or "",
        },
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    pay_payload = wechat_pay_service.get_pay_payload(order, package, data)
    return _serialize_payment_response(order, package, pay_payload)


def list_payment_orders(db: Session, current_user: AuthUser) -> dict:
    _get_user(db, current_user)
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.username == current_user.username,
    ).order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    return {"list": [_serialize_order(order) for order in orders], "total": len(orders)}


def get_payment_order(db: Session, current_user: AuthUser, order_no: str) -> dict:
    order = db.query(PaymentOrder).filter(
        PaymentOrder.order_no == order_no,
        PaymentOrder.username == current_user.username,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    package = db.query(SubscriptionPackage).filter(SubscriptionPackage.package_code == order.package_code).first()
    if not package:
        raise HTTPException(status_code=404, detail="订单关联套餐不存在")
    pay_payload = {
        "mode": "query",
        "scene": (order.extra_payload or {}).get("scene", "mini_program") if isinstance(order.extra_payload, dict) else "mini_program",
        "message": "订单查询接口不重复生成支付签名，如需重新拉起支付，请重新创建订单或补充预下单刷新接口。",
    }
    return _serialize_payment_response(order, package, pay_payload)


def get_refund_balance_stats(db: Session, current_user: AuthUser, data: PaymentRefundStatsRequest) -> dict:
    _assert_admin(current_user)
    query = db.query(PaymentOrder).filter(PaymentOrder.status.in_(["paid", REFUND_STATUS]))
    if data.username:
        query = query.filter(PaymentOrder.username == data.username)
    if data.orderNo:
        query = query.filter(PaymentOrder.order_no == data.orderNo)
    orders = query.order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc()).all()
    items = [_build_refund_balance(order, _get_subscription_for_order(db, order)) for order in orders]
    return {
        "list": items,
        "total": len(items),
        "summary": {
            "totalPaidAmount": round(sum(item["amount"] for item in items), 2),
            "totalHours": sum(item["totalHours"] for item in items),
            "usedHours": sum(item["usedHours"] for item in items),
            "refundableHours": sum(item["refundableHours"] for item in items),
            "refundableAmount": round(sum(item["refundableAmount"] for item in items), 2),
        },
    }


def apply_refund_by_hours(db: Session, current_user: AuthUser, data: PaymentRefundApplyRequest) -> dict:
    _assert_admin(current_user)
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == data.orderNo).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ["paid", REFUND_STATUS]:
        raise HTTPException(status_code=400, detail="仅支持已支付订单统计退款")

    subscription = _get_subscription_for_order(db, order)
    balance = _build_refund_balance(order, subscription)
    refunded_hours = balance["refundableHours"] if data.refundedHours is None else min(int(data.refundedHours), balance["refundableHours"])
    refund_payload = dict(order.extra_payload) if isinstance(order.extra_payload, dict) else {}
    refund_payload["refund"] = {
        "refundedHours": refunded_hours,
        "refundAmount": round(balance["hourlyAmount"] * refunded_hours, 2),
        "remark": data.refundRemark or "",
        "refundedAt": datetime.now(timezone.utc).isoformat(),
        "operator": current_user.username,
    }
    order.extra_payload = refund_payload
    order.status = REFUND_STATUS
    if subscription:
        subscription.status = REFUND_STATUS
        subscription.total_minutes = min(int(subscription.used_minutes or 0), int(subscription.total_minutes or 0))
    db.commit()
    db.refresh(order)
    return {"success": True, "refund": _build_refund_balance(order, subscription)}


def _sync_user_preferences_subscription(user: User, package: SubscriptionPackage, subscription: UserSubscription):
    prefs = dict(user.preferences) if isinstance(user.preferences, dict) else {}
    prefs["subscription"] = {
        "isTrialUser": bool(subscription.is_trial),
        "trialCompleted": bool(subscription.trial_completed),
        "planType": subscription.plan_type,
        "planName": subscription.plan_name,
        "status": subscription.status,
        "totalMinutes": int(subscription.total_minutes or 0),
        "usedMinutes": int(subscription.used_minutes or 0),
        "dailyLimitMinutes": int(subscription.daily_limit_minutes or 0),
        "dailyUsedMinutes": int(subscription.daily_used_minutes or 0),
        "expiresAt": subscription.end_at.isoformat() if subscription.end_at else "",
        "packageCode": package.package_code,
    }
    user.preferences = prefs


def _parse_paid_at(raw: str | None) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _assert_callback_amount(order: PaymentOrder, amount_total: int | None) -> None:
    if amount_total is None:
        return
    expected_total = int(round(float(order.amount or 0) * 100))
    if expected_total != int(amount_total):
        raise HTTPException(status_code=400, detail="回调金额与订单金额不一致")


def _ensure_subscription_for_paid_order(db: Session, order: PaymentOrder, package: SubscriptionPackage, paid_at: datetime) -> UserSubscription:
    existing = db.query(UserSubscription).filter(
        UserSubscription.source_order_no == order.order_no,
        UserSubscription.username == order.username,
    ).first()
    end_at = paid_at + timedelta(days=int(package.duration_days or 0)) if int(package.duration_days or 0) > 0 else None
    if existing:
        existing.status = "active" if order.status == "paid" else order.status
        existing.plan_name = package.package_name
        existing.plan_type = package.package_type
        existing.total_minutes = int(package.total_minutes or 0)
        existing.daily_limit_minutes = int(package.daily_limit_minutes or 0)
        existing.end_at = end_at
        return existing
    subscription = UserSubscription(
        username=order.username,
        package_code=package.package_code,
        plan_type=package.package_type,
        plan_name=package.package_name,
        status="active" if order.status == "paid" else order.status,
        is_trial=(package.package_type == "trial"),
        trial_completed=False,
        total_minutes=int(package.total_minutes or 0),
        used_minutes=0,
        daily_limit_minutes=int(package.daily_limit_minutes or 0),
        daily_used_minutes=0,
        last_reset_date=paid_at.date() if paid_at else None,
        start_at=paid_at,
        end_at=end_at,
        source_order_no=order.order_no,
        extra_payload={"payChannel": order.pay_channel},
    )
    db.add(subscription)
    return subscription


def handle_payment_callback(db: Session, data: PaymentCallbackRequest, headers: dict | None = None) -> dict:
    parsed = wechat_pay_service.parse_callback(data, headers)
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == parsed["orderNo"]).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    package = _get_package_or_404(db, order.package_code)
    user = db.query(User).filter(User.username == order.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="订单关联用户不存在")

    _assert_callback_amount(order, parsed.get("amountTotal"))
    paid_at = _parse_paid_at(parsed.get("paidAt"))

    if order.status == "paid":
        subscription = _ensure_subscription_for_paid_order(db, order, package, order.paid_at or paid_at)
        _sync_user_preferences_subscription(user, package, subscription)
        db.commit()
        return {
            "success": True,
            "idempotent": True,
            "message": "订单已支付，重复回调已忽略",
            "callbackMode": parsed["mode"],
            "verifyPending": parsed.get("verifyPending", False),
            "order": _serialize_order(order),
        }

    order.status = parsed.get("status") or "paid"
    order.third_party_order_no = parsed.get("transactionId") or order.third_party_order_no
    order.paid_at = paid_at
    order.callback_payload = {
        "mode": parsed["mode"],
        "verified": parsed.get("verified", False),
        "verifyPending": parsed.get("verifyPending", False),
        "headers": parsed.get("headers", {}),
        "payload": parsed.get("rawPayload", {}),
        "realCallbackTodo": parsed.get("realCallbackTodo", {}),
    }

    subscription = _ensure_subscription_for_paid_order(db, order, package, paid_at)
    _sync_user_preferences_subscription(user, package, subscription)
    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "idempotent": False,
        "callbackMode": parsed["mode"],
        "verified": parsed.get("verified", False),
        "verifyPending": parsed.get("verifyPending", False),
        "order": _serialize_order(order),
        "subscription": {
            "username": subscription.username,
            "packageCode": subscription.package_code,
            "planType": subscription.plan_type,
            "planName": subscription.plan_name,
            "status": subscription.status,
            "totalMinutes": subscription.total_minutes,
            "dailyLimitMinutes": subscription.daily_limit_minutes,
            "startAt": subscription.start_at.isoformat() if subscription.start_at else "",
            "endAt": subscription.end_at.isoformat() if subscription.end_at else "",
        },
    }
