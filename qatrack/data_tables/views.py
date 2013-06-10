import json

import urllib

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic import ListView


#============================================================================
class BaseDataTablesDataSource(ListView):
    """This view serves a page with a pre-rendered"""

    model = None
    queryset = None
    initial_orderings = []
    max_display_length = 500
    page_title = "Generic Data Tables Template View"

    #---------------------------------------------------------------------------
    def render_to_response(self, context):
        if self.request.is_ajax():
            return HttpResponse(json.dumps(context), content_type='application/json')
        else:
            return super(BaseDataTablesDataSource, self).render_to_response(context)

    #---------------------------------------------------------------------------
    def get_context_data(self, *args, **kwargs):
        context = super(BaseDataTablesDataSource, self).get_context_data(*args, **kwargs)

        table_data = self.get_table_context_data(context)
        if self.request.is_ajax():
            return table_data
        else:
            context.update(table_data)
            return self.get_template_context_data(context)

    #----------------------------------------------------------------------
    def get_table_context_data(self, base_context):
        """return a dictionary of all required values for rendering a Data Table"""

        all_objects = base_context["object_list"]

        self.set_search_filter_context()

        self.set_columns()
        self.set_orderings()
        self.set_filters()

        self.filtered_objects = all_objects.filter(*self.filters).order_by(*self.orderings)

        self.set_current_page_objects()
        self.tabulate_data()

        context = {
            "data": self.table_data,
            "iTotalRecords": all_objects.count(),
            "iTotalDisplayRecords": self.filtered_objects.count(),
            "sEcho": self.search_filter_context.get("sEcho"),
        }

        return context

    #----------------------------------------------------------------------
    def set_search_filter_context(self):
        """create a search and filter context, overridng any cookie values
        with request values.  This is required when "Sticky" DataTables filters
        are used """

        self.search_filter_context = {}

        try:
            for k, v in self.request.COOKIES.items():
                if k.startswith("SpryMedia_DataTables"):
                    break
            else:
                raise KeyError

            cookie_filters = json.loads(urllib.unquote(v))

            for idx, search in enumerate(cookie_filters["aoSearchCols"]):
                for k, v in search.items():
                    self.search_filter_context["%s_%d" % (k, idx)] = v

            self.search_filter_context["iSortingCols"] = 0
            for idx, (col, dir_, _) in enumerate(cookie_filters["aaSorting"]):
                self.search_filter_context["iSortCol_%d" % (idx)] = col
                self.search_filter_context["sSortDir_%d" % (idx)] = dir_
                self.search_filter_context["iSortingCols"] += 1

            self.search_filter_context["iDisplayLength"] = cookie_filters["iLength"]
            self.search_filter_context["iDisplayStart"] = cookie_filters["iStart"]
            self.search_filter_context["iDisplayEnd"] = cookie_filters["iEnd"]

        except KeyError:
            pass

        self.search_filter_context.update(self.request.GET.dict())

    #---------------------------------------------------------------------------
    def set_columns(self):
        """Return an interable (of length N-Columns) of three-tuples consisting of:
            1) A callable which accepts a model instance and returns the display value
            for the column e.g. lambda instance: instance.name
            2) A string representing a Django filter for this column (e.g. name__icontains)
            or None to disable filtering
            3) A string representing a model field to order instances (e.g. name) This can also be
            an iterable of strings to handle generic foreign key cases  (e.g.
            (mycontenttype1__name, mycontenttype2__someotherfield)

            This function must be overridden in child class"""
        self.columns = ()
        raise NotImplementedError

    #----------------------------------------------------------------------
    def set_orderings(self):
        """Figure out which columns user wants to order on"""
        n_orderings = int(self.search_filter_context.get("iSortingCols", 0))

        if n_orderings == 0:
            self.orderings = self.initial_orderings
            return

        order_cols = []
        for x in range(n_orderings):
            col = int(self.search_filter_context.get("iSortCol_%d" % x))
            direction = "" if self.search_filter_context.get("sSortDir_%d" % x, "asc") == "asc" else "-"
            order_cols.append((col, direction))

        self.orderings = []
        for col, direction in order_cols:
            display, search, ordering = self.columns[col]
            if ordering:
                if isinstance(ordering, basestring):
                    self.orderings.append("%s%s" % (direction, ordering))
                else:
                    for o in ordering:
                        self.orderings.append("%s%s" % (direction, o))

    #----------------------------------------------------------------------
    def set_filters(self):
        """Create filters made up of Q objects"""
        self.filters = []

        for col, (display, search, ordering) in enumerate(self.columns):

            search_term = self.search_filter_context.get("sSearch_%d" % col)

            if search and search_term:
                if search_term == "null":
                    search_term = None

                if not isinstance(search, basestring):
                    #handle case where we are filtering on a Generic Foreign Key field
                    f = Q()
                    for s, ct in search:
                        f != Q(**{s: search_term, "content_type": ct})
                else:
                    f = Q(**{search: search_term})
                self.filters.append(f)

    #----------------------------------------------------------------------
    def set_current_page_objects(self):
        per_page = int(self.search_filter_context.get("iDisplayLength", self.max_display_length))
        per_page = min(per_page, self.max_display_length)
        offset = int(self.search_filter_context.get("iDisplayStart", 0))
        self.cur_page_objects = self.filtered_objects[offset:offset + per_page]

    #----------------------------------------------------------------------
    def tabulate_data(self):
        self.table_data = []
        for obj in self.cur_page_objects:
            row = []
            for col, (display, search, ordering) in enumerate(self.columns):
                if callable(display):
                    display = display(obj)
                row.append(display)
            self.table_data.append(row)

    #----------------------------------------------------------------------
    def get_page_title(self):
        return self.page_title

    #----------------------------------------------------------------------
    def get_template_context_data(self, context):
        context["page_title"] = self.get_page_title()
        return context

