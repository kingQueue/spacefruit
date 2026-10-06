from django.urls import path
from .views import add_plant, confirm_plan, harvest, load_seeds, marketplace_listing_action, marketplace_listings, remove_plant, replant, start_monitoring, start_planting, start_workflow, state, thumbnail

urlpatterns = [
    path("api/state", state),
    path("api/start", start_workflow),
    path("api/add-plant", add_plant),
    path("api/remove-plant", remove_plant),
    path("api/confirm", confirm_plan),
    path("api/load-seeds", load_seeds),
    path("api/start-planting", start_planting),
    path("api/start-monitoring", start_monitoring),
    path("api/harvest", harvest),
    path("api/replant", replant),
    path("api/marketplace/listings", marketplace_listings),
    path("api/marketplace/listings/<str:listing_id>", marketplace_listing_action),
    path("thumbs/<path:name>", thumbnail),
]
