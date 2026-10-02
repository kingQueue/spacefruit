from django.urls import path
from .views import add_plant, confirm_plan, load_seeds, remove_plant, start_monitoring, start_planting, start_workflow, state, thumbnail

urlpatterns = [
    path("api/state", state),
    path("api/start", start_workflow),
    path("api/add-plant", add_plant),
    path("api/remove-plant", remove_plant),
    path("api/confirm", confirm_plan),
    path("api/load-seeds", load_seeds),
    path("api/start-planting", start_planting),
    path("api/start-monitoring", start_monitoring),
    path("thumbs/<path:name>", thumbnail),
]
