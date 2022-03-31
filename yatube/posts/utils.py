from django.conf import settings
from django.core.paginator import Paginator


def get_page(request, queryset):
    paginator = Paginator(queryset, settings.AMOUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
