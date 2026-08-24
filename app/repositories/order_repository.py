import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from app.config import settings
from app.models import Order, Customer

logger = logging.getLogger(__name__)

class OrderRepository:
    """Repository for accessing the immutable Trendly orders dataset."""
    
    def __init__(self, orders_file_path: Optional[Path] = None):
        self.file_path = orders_file_path or settings.ORDERS_FILE
        self._orders_by_id: Dict[str, Order] = {}
        self._customers_by_id: Dict[str, Customer] = {}
        self._orders_by_customer: Dict[str, List[Order]] = {}
        self._load_data()

    def _load_data(self):
        """Load and parse orders.json without modifying the original data."""
        if not self.file_path.exists():
            logger.error(f"Orders file not found at {self.file_path}")
            raise FileNotFoundError(f"Orders file not found at {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # Parse customers
        for cust_dict in raw_data.get("customers", []):
            customer = Customer(**cust_dict)
            self._customers_by_id[customer.customer_id] = customer

        # Parse orders
        for ord_dict in raw_data.get("orders", []):
            order = Order(**ord_dict)
            self._orders_by_id[order.order_id] = order
            
            if order.customer_id not in self._orders_by_customer:
                self._orders_by_customer[order.customer_id] = []
            self._orders_by_customer[order.customer_id].append(order)

        logger.info(f"Loaded {len(self._orders_by_id)} orders and {len(self._customers_by_id)} customers.")

    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve an order by ID (case-insensitive normalized)."""
        if not order_id:
            return None
        normalized_id = order_id.strip().upper()
        # Support searching without hyphen (e.g. TR4521 -> TR-4521)
        if normalized_id.startswith("TR") and "-" not in normalized_id:
            normalized_id = f"TR-{normalized_id[2:]}"
        return self._orders_by_id.get(normalized_id)

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Retrieve customer details by ID."""
        if not customer_id:
            return None
        return self._customers_by_id.get(customer_id.strip().upper())

    def get_orders_by_customer(self, customer_id: str) -> List[Order]:
        """Retrieve all orders belonging to a customer."""
        if not customer_id:
            return []
        return self._orders_by_customer.get(customer_id.strip().upper(), [])

    def get_all_orders(self) -> List[Order]:
        """Retrieve list of all orders."""
        return list(self._orders_by_id.values())

order_repository = OrderRepository()
