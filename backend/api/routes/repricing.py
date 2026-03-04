"""
Repricing & Bulk Actions API Routes
Automated pricing and bulk price management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ConfigDict, BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User, RepricingRule
from api.dependencies import get_current_user
from services.repricing_service import get_repricing_service
from services.activity_service import log_activity

router = APIRouter(prefix="/repricing", tags=["Repricing & Bulk Actions"])


# Pydantic Models
class BulkActionRequest(BaseModel):
    product_ids: List[int]
    action: str  # "match_lowest", "undercut", "margin_based", "dynamic"
    params: Dict[str, Any]


class RepricingRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str  # "match_lowest", "undercut", "margin_based", "dynamic", "map_protected"
    config: Dict[str, Any]
    product_id: Optional[int] = None  # Null = applies to all products
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    map_price: Optional[float] = None
    priority: int = 0
    auto_apply: bool = False
    requires_approval: bool = True


class RepricingRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    map_price: Optional[float] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    auto_apply: Optional[bool] = None
    requires_approval: Optional[bool] = None


class RepricingRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rule_type: str
    config: Dict[str, Any]
    product_id: Optional[int]
    min_price: Optional[float]
    max_price: Optional[float]
    map_price: Optional[float]
    enabled: bool
    priority: int
    auto_apply: bool
    requires_approval: bool
    last_applied_at: Optional[Any]
    application_count: int
    success_count: int
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


# Bulk Action Endpoints

@router.post("/bulk/match-lowest")
async def bulk_match_lowest(
    product_ids: List[int],
    margin_amount: float = 0,
    margin_pct: float = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Match lowest competitor price with optional margin

    - **product_ids**: List of products to reprice
    - **margin_amount**: Stay this amount below lowest (e.g., 0.50)
    - **margin_pct**: Stay this percentage below lowest (e.g., 5.0 for 5%)

    Returns suggested price changes for review
    """
    repricing_service = get_repricing_service(db, current_user)

    result = repricing_service.match_lowest_competitor(
        product_ids,
        margin_amount,
        margin_pct
    )

    strategy_name = "match_lowest"
    count = result.get("products_processed", 0)
    log_activity(db, current_user.id, "bulk.reprice", "rule", f"Bulk repriced {count} product(s) using {strategy_name}", metadata={"strategy": strategy_name, "product_count": count})
    db.flush()

    return result


@router.post("/bulk/undercut")
async def bulk_undercut(
    product_ids: List[int],
    undercut_amount: Optional[float] = None,
    undercut_pct: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Price below all competitors by fixed amount or percentage

    - **product_ids**: List of products to reprice
    - **undercut_amount**: Price this much below lowest (e.g., 1.00)
    - **undercut_pct**: Price this percentage below lowest (e.g., 10.0 for 10%)

    Returns suggested price changes for review
    """
    repricing_service = get_repricing_service(db, current_user)

    result = repricing_service.undercut_all_competitors(
        product_ids,
        undercut_amount,
        undercut_pct
    )

    strategy_name = "undercut"
    count = result.get("products_processed", 0)
    log_activity(db, current_user.id, "bulk.reprice", "rule", f"Bulk repriced {count} product(s) using {strategy_name}", metadata={"strategy": strategy_name, "product_count": count})
    db.flush()

    return result


@router.post("/bulk/margin-based")
async def bulk_margin_based(
    product_ids: List[int],
    cost_price: float,
    margin_pct: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set price based on cost + margin percentage

    - **product_ids**: List of products
    - **cost_price**: Product cost
    - **margin_pct**: Desired profit margin (e.g., 40 for 40%)

    Returns suggested prices with profit calculations
    """
    repricing_service = get_repricing_service(db, current_user)

    result = repricing_service.set_margin_based_pricing(
        product_ids,
        cost_price,
        margin_pct
    )

    strategy_name = "margin_based"
    count = result.get("products_processed", 0)
    log_activity(db, current_user.id, "bulk.reprice", "rule", f"Bulk repriced {count} product(s) using {strategy_name}", metadata={"strategy": strategy_name, "product_count": count})
    db.flush()

    return result


@router.post("/bulk/dynamic")
async def bulk_dynamic(
    product_ids: List[int],
    conditions: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply dynamic pricing based on multiple factors

    Conditions can include:
    - **low_stock_increase**: % to increase if low stock
    - **high_competition_decrease**: % to decrease if high competition
    - **weekend_increase**: % to increase on weekends
    - **demand_multiplier**: Multiplier for trending products

    Returns suggested prices with adjustments applied
    """
    repricing_service = get_repricing_service(db, current_user)

    result = repricing_service.apply_dynamic_adjustment(
        product_ids,
        conditions
    )

    strategy_name = "dynamic"
    count = result.get("products_processed", 0)
    log_activity(db, current_user.id, "bulk.reprice", "rule", f"Bulk repriced {count} product(s) using {strategy_name}", metadata={"strategy": strategy_name, "product_count": count})
    db.flush()

    return result


@router.post("/bulk/check-map")
async def check_map_violations(
    product_ids: List[int],
    map_prices: Dict[int, float],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if suggested prices violate Minimum Advertised Price

    - **product_ids**: Products to check
    - **map_prices**: Dict of {product_id: map_price}

    Returns list of potential MAP violations
    """
    repricing_service = get_repricing_service(db, current_user)

    result = repricing_service.check_map_compliance(
        product_ids,
        map_prices
    )

    return result


# Repricing Rules Endpoints

@router.post("/rules", response_model=RepricingRuleResponse)
async def create_repricing_rule(
    rule: RepricingRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new repricing rule

    Rule Types:
    - **match_lowest**: Match lowest competitor (config: {margin_amount, margin_pct})
    - **undercut**: Undercut competitors (config: {amount, percentage})
    - **margin_based**: Cost + margin (config: {cost, margin_pct})
    - **dynamic**: Complex rules (config: {conditions})
    - **map_protected**: Never go below MAP (config: {map_price})

    Example config:
    ```json
    {
      "name": "Match Amazon -$0.50",
      "rule_type": "match_lowest",
      "config": {"margin_amount": 0.50},
      "min_price": 10.00,
      "auto_apply": false
    }
    ```
    """
    repricing_service = get_repricing_service(db, current_user)

    new_rule = repricing_service.create_repricing_rule({
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "config": rule.config,
        "product_id": rule.product_id,
        "min_price": rule.min_price,
        "max_price": rule.max_price,
        "map_price": rule.map_price,
        "priority": rule.priority,
        "auto_apply": rule.auto_apply,
        "requires_approval": rule.requires_approval
    })

    log_activity(db, current_user.id, "rule.create", "rule", f"Created repricing rule '{new_rule.name}'", entity_type="rule", entity_id=new_rule.id, entity_name=new_rule.name, metadata={"rule_type": new_rule.rule_type})
    db.flush()

    return new_rule


@router.get("/rules", response_model=List[RepricingRuleResponse])
async def get_repricing_rules(
    product_id: Optional[int] = None,
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all repricing rules for current user

    - **product_id**: Filter by specific product (optional)
    - **enabled_only**: Only return enabled rules
    """
    query = db.query(RepricingRule).filter(
        RepricingRule.user_id == current_user.id
    )

    if product_id:
        query = query.filter(
            (RepricingRule.product_id == product_id) |
            (RepricingRule.product_id == None)
        )

    if enabled_only:
        query = query.filter(RepricingRule.enabled == True)

    rules = query.order_by(RepricingRule.priority.desc()).all()

    return rules


@router.get("/rules/{rule_id}", response_model=RepricingRuleResponse)
async def get_repricing_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific repricing rule by ID"""
    rule = db.query(RepricingRule).filter(
        RepricingRule.id == rule_id,
        RepricingRule.user_id == current_user.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Repricing rule not found")

    return rule


@router.put("/rules/{rule_id}", response_model=RepricingRuleResponse)
async def update_repricing_rule(
    rule_id: int,
    update: RepricingRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a repricing rule"""
    rule = db.query(RepricingRule).filter(
        RepricingRule.id == rule_id,
        RepricingRule.user_id == current_user.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Repricing rule not found")

    # Update fields
    if update.name is not None:
        rule.name = update.name
    if update.description is not None:
        rule.description = update.description
    if update.config is not None:
        rule.config = update.config
    if update.min_price is not None:
        rule.min_price = update.min_price
    if update.max_price is not None:
        rule.max_price = update.max_price
    if update.map_price is not None:
        rule.map_price = update.map_price
    if update.priority is not None:
        rule.priority = update.priority
    if update.enabled is not None:
        rule.enabled = update.enabled
    if update.auto_apply is not None:
        rule.auto_apply = update.auto_apply
    if update.requires_approval is not None:
        rule.requires_approval = update.requires_approval

    from datetime import datetime
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    return rule


@router.delete("/rules/{rule_id}")
async def delete_repricing_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a repricing rule"""
    rule = db.query(RepricingRule).filter(
        RepricingRule.id == rule_id,
        RepricingRule.user_id == current_user.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Repricing rule not found")

    log_activity(db, current_user.id, "rule.delete", "rule", f"Deleted repricing rule '{rule.name}'", entity_type="rule", entity_id=rule_id, entity_name=rule.name)
    db.delete(rule)
    db.commit()

    return {"success": True, "message": "Repricing rule deleted"}


@router.post("/rules/{rule_id}/apply")
async def apply_repricing_rule(
    rule_id: int,
    product_ids: Optional[List[int]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply a repricing rule to products

    - **rule_id**: ID of rule to apply
    - **product_ids**: Optional list of specific products (overrides rule's product_id)

    Returns suggested price changes based on rule configuration
    """
    repricing_service = get_repricing_service(db, current_user)

    rule = db.query(RepricingRule).filter(
        RepricingRule.id == rule_id,
        RepricingRule.user_id == current_user.id
    ).first()

    result = repricing_service.apply_repricing_rule(rule_id, product_ids)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    applied_count = result.get("products_processed", 0)
    if rule:
        log_activity(db, current_user.id, "rule.apply", "rule", f"Applied rule '{rule.name}' to {applied_count} product(s)", entity_type="rule", entity_id=rule_id, entity_name=rule.name, metadata={"applied_count": applied_count})
        db.flush()

    return result


@router.post("/rules/{rule_id}/toggle")
async def toggle_repricing_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable/disable a repricing rule"""
    rule = db.query(RepricingRule).filter(
        RepricingRule.id == rule_id,
        RepricingRule.user_id == current_user.id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Repricing rule not found")

    rule.enabled = not rule.enabled
    log_activity(db, current_user.id, "rule.toggle", "rule", f"{'Enabled' if rule.enabled else 'Disabled'} rule '{rule.name}'", entity_type="rule", entity_id=rule.id, entity_name=rule.name, metadata={"enabled": rule.enabled})
    db.commit()

    return {
        "success": True,
        "rule_id": rule.id,
        "enabled": rule.enabled
    }
