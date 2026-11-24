"""
Serves the HTML frontend. Pages are thin Jinja2 shells; all data comes from
the JSON API in app/static/js/app.js using the JWT stored in the browser
after login. This keeps the frontend decoupled from the API so the same API
could later be consumed by a mobile app or another client.
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def _render(request: Request, template: str, **extra):
    return templates.TemplateResponse(request, template, {**extra})


@router.get("/")
def home(request: Request):
    return _render(request, "index.html", title="OrderFlow")


@router.get("/login")
def login_page(request: Request):
    return _render(request, "login.html", title="Login")


@router.get("/register")
def register_page(request: Request):
    return _render(request, "register.html", title="Register")


@router.get("/dashboard")
def dashboard_page(request: Request):
    return _render(request, "dashboard.html", title="Dashboard")


@router.get("/products")
def products_page(request: Request):
    return _render(request, "products.html", title="Products")


@router.get("/products/{product_id}")
def product_detail_page(request: Request, product_id: int):
    return _render(request, "product_detail.html", title="Product Details", product_id=product_id)


@router.get("/orders/new")
def create_order_page(request: Request):
    return _render(request, "create_order.html", title="Create Order")


@router.get("/orders")
def my_orders_page(request: Request):
    return _render(request, "my_orders.html", title="My Orders")


@router.get("/orders/{order_id}")
def order_detail_page(request: Request, order_id: int):
    return _render(request, "order_detail.html", title="Order Details", order_id=order_id)


@router.get("/profile")
def profile_page(request: Request):
    return _render(request, "profile.html", title="Profile")


@router.get("/admin")
def admin_dashboard_page(request: Request):
    return _render(request, "admin_dashboard.html", title="Admin Dashboard")


@router.get("/admin/products")
def admin_products_page(request: Request):
    return _render(request, "admin_products.html", title="Manage Products")


@router.get("/admin/orders")
def admin_orders_page(request: Request):
    return _render(request, "admin_orders.html", title="Manage Orders")


@router.get("/admin/users")
def admin_users_page(request: Request):
    return _render(request, "admin_users.html", title="Customers")


@router.get("/admin/events")
def admin_events_page(request: Request):
    return _render(request, "admin_events.html", title="Event Processing Logs")
