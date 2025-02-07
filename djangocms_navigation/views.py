from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, View

from cms.models import Page

from djangocms_navigation.utils import is_model_supported, supported_models


class MenuContentPreviewView(TemplateView):
    menu_content_model = None
    menu_item_model = None
    template_name = "admin/djangocms_navigation/menucontent/preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        menu_content = get_object_or_404(
            self.menu_content_model._base_manager, pk=self.kwargs.get("menu_content_id")
        )
        annotated_list = self.menu_item_model.get_annotated_list(parent=menu_content.root)
        context.update({
            "annotated_list": annotated_list,
            "opts": self.menu_item_model._meta
        })
        return context


class ContentObjectSelect2View(View):
    menu_content_model = None

    def get(self, request, *args, **kwargs):

        content_type_id = self.request.GET.get("content_type_id", None)
        # Return http bad request if there is no content_type_id provided in request
        if not content_type_id:
            return HttpResponseBadRequest()

        # return http bad request if content_type not exist in db
        try:
            content_object = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return HttpResponseBadRequest()

        # return http bad request if content type is not registered to use navigation app
        model = content_object.model_class()
        if not is_model_supported(self.menu_content_model, model):
            return HttpResponseBadRequest()

        data = {
            "results": [{"text": str(obj), "id": obj.pk} for obj in self.get_data()]
        }
        return JsonResponse(data)

    def get_data(self):
        content_type_id = self.request.GET.get("content_type_id", None)
        query = self.request.GET.get("query", None)
        site = self.request.GET.get("site")
        content_object = ContentType.objects.get_for_id(content_type_id)
        model = content_object.model_class()

        try:
            # If versioning is enabled then get versioning queryset for model
            app_config = apps.get_app_config("djangocms_versioning")
            versionable_item = app_config.cms_extension.versionables_by_grouper[model]
            queryset = versionable_item.grouper_choices_queryset()
        except (LookupError, KeyError):
            queryset = model.objects.all()

        try:
            pk = int(self.request.GET.get("pk"))
        except (TypeError, ValueError):
            pk = None

        if site:
            if hasattr(model.objects, "on_site"):
                queryset = queryset.on_site(site)
            elif hasattr(model, "site"):
                queryset = queryset.filter(site=site)

        if pk:
            queryset = queryset.filter(pk=pk)

        if query:

            # TODO: filter by language and publish state
            # For Page model filter query by pagecontent title
            if model == Page:
                queryset = queryset.filter(pagecontent_set__title__icontains=query)
            else:
                # Non page model should work using filter against field in queryset
                options = {}
                search_fields = supported_models(self.menu_content_model).get(model)
                if search_fields:
                    for field in search_fields:
                        options[field] = query
                    queryset = queryset.filter(**options)

        return queryset


class MessageStorageView(View):

    def get(self, request, *args, **kwargs):
        storage = get_messages(request)
        data = {'messages': [{'message': m.message, 'level': m.level_tag} for m in storage]}

        return JsonResponse(data)
