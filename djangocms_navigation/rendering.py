from django.template.response import TemplateResponse


def render_menu(request, menucontent):
    template = 'djangocms_navigation/admin/preview.html'
    context = {'menucontent': menucontent}
    return TemplateResponse(request, template, context)
