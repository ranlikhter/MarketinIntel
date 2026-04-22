"""
Repricing & Bulk Actions API Routes
Automated pricing and bulk price management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import ConfigDict, BaseModel
from typing import List, Dict, Any, Optional

from database.connection import get_db
from database.models import User, RepricingRule, ProductMonitored, CompetitorMatch
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

@router.post("/rules/preview")
async def preview_repricing_rule(
    rule: RepricingRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    POST /repricing/rules/preview

    Simulate a rule without saving it.  Returns the number of affected products,
    average current price, average suggested price, and average margin impact (%).
    Used to show an impact summary before the user commits to creating the rule.
    """
    from sqlalchemy import func as sqlfunc

    # 1. Determine affected products
    base_q = db.query(ProductMonitored).filter(
        ProductMonitored.user_id == current_user.id,
        ProductMonitored.my_price.isnot(None),
    )
    if rule.product_id:
        base_q = base_q.filter(ProductMonitored.id == rule.product_id)
    products = base_q.all()

    if not products:
        return {"affected_products": 0, "avg_current": None, "avg_suggested": None, "margin_impact": None}

    product_ids = [p.id for p in products]
    products_by_id = {p.id: p for p in products}

    # 2. Batch-load lowest competitor prices
    lowest_by_product: dict = {}
    rows = (
        db.query(
            CompetitorMatch.monitored_product_id,
            sqlfunc.min(CompetitorMatch.latest_price).label("lowest"),
        )
        .filter(
            CompetitorMatch.monitored_product_id.in_(product_ids),
            CompetitorMatch.latest_price.isnot(None),
        )
        .group_by(CompetitorMatch.monitored_product_id)
        .all()
    )
    for row in rows:
        lowest_by_product[row.monitored_product_id] = row.lowest

    # 3. Simulate suggested price per product
    cfg = rule.config or {}
    suggestions = []
    for p in products:
        current = p.my_price
        lowest = lowest_by_product.get(p.id)
        suggested = None

        if rule.rule_type == "match_lowest" and lowest is not None:
            margin = cfg.get("margin_amount") or (lowest * cfg.get("margin_pct", 0) / 100)
            suggested = lowest + margin
        elif rule.rule_type == "undercut" and lowest is not None:
            amt = cfg.get("amount") or (lowest * cfg.get("percentage", 0) / 100)
            suggested = lowest - amt
        elif rule.rule_type == "margin_based":
            cost = cfg.get("cost", 0)
            margin_pct = cfg.get("margin_pct", 0)
            suggested = cost * (1 + margin_pct / 100) if cost else None
        elif rule.rule_type in ("dynamic", "map_protected"):
            suggested = current  # can't meaningfully simulate without data

        if suggested is None:
            continue

        # Apply rule constraints
        if rule.min_price and suggested < rule.min_price:
            suggested = rule.min_price
        if rule.max_price and suggested > rule.max_price:
            suggested = rule.max_price
        if rule.map_price and suggested < rule.map_price:
            suggested = rule.map_price

        suggestions.append((current, round(suggested, 2)))

    if not suggestions:
        return {
            "affected_products": len(products),
            "avg_current": None,
            "avg_suggested": None,
            "margin_impact": None,
        }

    avg_current = round(sum(c for c, _ in suggestions) / len(suggestions), 2)
    avg_suggested = round(sum(s for _, s in suggestions) / len(suggestions), 2)
    margin_impact = round((avg_suggested - avg_current) / avg_current * 100, 2) if avg_current else None

    return {
        "affected_products": len(suggestions),
        "avg_current": avg_current,
        "avg_suggested": avg_suggested,
        "margin_impact": margin_impact,
    }


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


# ============================================================
# MAP Violation Report
# ============================================================

@router.get("/map-violations")
async def get_map_violations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Identify competitors currently selling below your Minimum Advertised Price (MAP).

    Scans all repricing rules that have a `map_price` set and cross-references
    current competitor prices for the associated product(s). Returns a ranked
    list of violations sorted by the largest discount below MAP.

    Use this report to file MAP complaints with manufacturers or flag rogue sellers.
    """
    # Fetch user's MAP-protected rules
    map_rules = db.query(RepricingRule).filter(
        RepricingRule.user_id == current_user.id,
        RepricingRule.map_price.isnot(None),
        RepricingRule.enabled == True,
    ).all()

    violations = []

    if not map_rules:
        return {
            "success": True,
            "total_violations": 0,
            "severity_summary": {"high": 0, "medium": 0, "low": 0},
            "map_rules_checked": 0,
            "violations": [],
        }

    # ── Batch load — O(2 queries) instead of O(rules × products × matches) ────
    # 1. Load all relevant products in one shot
    has_global_rule = any(r.product_id is None for r in map_rules)
    specific_ids = {r.product_id for r in map_rules if r.product_id is not None}

    if has_global_rule:
        all_products = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == current_user.id
        ).all()
    else:
        all_products = db.query(ProductMonitored).filter(
            ProductMonitored.user_id == current_user.id,
            ProductMonitored.id.in_(specific_ids),
        ).all()

    products_by_id = {p.id: p for p in all_products}

    # 2. Load all competitor matches for these products in one query
    if not products_by_id:
        return {
            "success": True,
            "total_violations": 0,
            "severity_summary": {"high": 0, "medium": 0, "low": 0},
            "map_rules_checked": len(map_rules),
            "violations": [],
        }

    all_matches = db.query(CompetitorMatch).filter(
        CompetitorMatch.monitored_product_id.in_(list(products_by_id.keys())),
        CompetitorMatch.latest_price.isnot(None),
    ).all()

    from collections import defaultdict
    matches_by_product: dict = defaultdict(list)
    for m in all_matches:
        matches_by_product[m.monitored_product_id].append(m)

    # 3. Apply rules in Python — zero additional DB queries
    for rule in map_rules:
        map_price = rule.map_price
        applicable = (
            [products_by_id[rule.product_id]]
            if rule.product_id and rule.product_id in products_by_id
            else list(products_by_id.values())
        )

        for product in applicable:
            for match in matches_by_product[product.id]:
                if match.latest_price >= map_price:
                    continue
                below_by = round(map_price - match.latest_price, 2)
                below_pct = round(below_by / map_price * 100, 2)

                violations.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "product_id": product.id,
                    "product_title": product.title,
                    "product_sku": product.sku,
                    "map_price": map_price,
                    "competitor": match.competitor_name,
                    "competitor_url": match.competitor_url,
                    "competitor_price": match.latest_price,
                    "below_map_by": below_by,
                    "below_map_pct": below_pct,
                    "last_scraped": (
                        match.last_scraped_at.isoformat() if match.last_scraped_at else None
                    ),
                    "severity": (
                        "high" if below_pct >= 10
                        else "medium" if below_pct >= 5
                        else "low"
                    ),
                })

    # Sort: largest violation first
    violations.sort(key=lambda x: -x["below_map_pct"])

    summary = {
        "high": sum(1 for v in violations if v["severity"] == "high"),
        "medium": sum(1 for v in violations if v["severity"] == "medium"),
        "low": sum(1 for v in violations if v["severity"] == "low"),
    }

    return {
        "success": True,
        "total_violations": len(violations),
        "severity_summary": summary,
        "map_rules_checked": len(map_rules),
        "violations": violations,
    }
