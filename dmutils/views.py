from abc import ABCMeta, abstractmethod
import csv
import enum
from flask import abort, request, Response
from flask.views import View
from io import BytesIO
from odf.style import TextProperties, TableRowProperties, TableColumnProperties, TableCellProperties, FontFace

from dmutils import csv_generator
from dmutils import ods


class DownloadFileView(View):
    """An abstract base class appropriate for subclassing in the frontend apps when the user needs to be able to
    download some data as a CSV or ODF file. All abstract methods must be implemented on the subclass; all other
    methods should be able to remain as-is to support handling and dispatching the request."""
    __metaclass__ = ABCMeta

    FILETYPES = enum.Enum('Filetypes', ['CSV', 'ODF'])

    def __init__(self, **kwargs):
        self.data_api_client = None
        self.search_api_client = None
        self.content_loader = None
        self.request = request

        super(View, self).__init__(**kwargs)

    def _pre_request_hook(self, **kwargs):
        """A hook that can be used to implement any logic that should be run before the main download file process."""
        pass

    def _post_request_hook(self, response, **kwargs):
        """A hook that can be used to implement any logic that should be run after the main download file process,
        and immediately before sending the response to the user."""
        pass

    @abstractmethod
    def _init_clients(self):
        """Grants access to the required clients/loaders in the View; implement and assign as appropriate."""
        self.data_api_client = None
        self.search_api_client = None
        self.content_loader = None

    @abstractmethod
    def determine_filetype(self):
        """Logic to tell the View which filetype to generate; must return a choice from DownloadFileView.FILETYPES"""
        return DownloadFileView.FILETYPES.ODF

    @abstractmethod
    def get_file_context(self):
        """Should return a dictionary containing any data required by the generation routines.

        Required keys:
         * `filename`: without a file extension"""
        return {'filename': 'my-download'}

    @abstractmethod
    def generate_csv_rows(self, file_context):
        """Should return a nested list of rows+cells, [[heading1, heading2], [data1, data2], ...]"""
        return [['heading 1', 'heading 2'], ['row 1 column 1', 'row 1 column 2']]

    @abstractmethod
    def generate_ods(self, spreadsheet, file_context):
        """Should return an instance of dmutils.ods.Spreadsheet()"""
        sheet = self.create_default_ods()
        return sheet

    def create_csv_response(self, file_context=None):
        """Build a csv file in memory and return the Response for this view ready for dispatch."""
        csv_rows = self.generate_csv_rows(file_context)

        return Response(
            csv_generator.iter_csv(csv_rows, quoting=csv.QUOTE_ALL),
            mimetype='text/csv',
            headers={
                "Content-Disposition": (
                    "attachment;filename={}.csv"
                ).format(file_context['filename']),
                "Content-Type": "text/csv; header=present"
            }
        ), 200

    @staticmethod
    def create_default_ods():
        """Create a dmutils.ods.SpreadSheet pre-configured with some default styles, ready for population with data
        appropriate for the subclass View."""
        spreadsheet = ods.SpreadSheet()

        # Add the font we will use for the entire spreadsheet.
        spreadsheet.add_font(FontFace(name="Arial", fontfamily="Arial"))

        # Add some default styles for columns.
        spreadsheet.add_style("col-default", "table-column", (
            TableColumnProperties(columnwidth="150pt", breakbefore="auto", useoptimalcolumnwidth="true"),
        ))

        spreadsheet.add_style("col-wide", "table-column", (
            TableColumnProperties(columnwidth="300pt"),
        ), parentstylename="col-default")

        # Add some default styles for rows.
        spreadsheet.add_style("row-default", "table-row", (
            TableRowProperties(breakbefore="auto", useoptimalrowheight="true"),
        ))

        spreadsheet.add_style("row-tall", "table-row", (
            TableRowProperties(rowheight="50pt"),
        ), parentstylename="row-default")

        # Add some default styles for cells.
        spreadsheet.add_style("cell-default", "table-cell", (
            TableCellProperties(wrapoption="wrap", verticalalign="top"),
            TextProperties(fontfamily="Arial", fontnameasian="Arial", fontnamecomplex="Arial", fontsize="10pt"),
        ), parentstylename="Default")

        spreadsheet.add_style("cell-header", "table-cell", (
            TableCellProperties(wrapoption="wrap", verticalalign="top"),
            TextProperties(fontweight="bold"),
        ), parentstylename="cell-default")

        return spreadsheet

    def create_ods_response(self, file_context=None):
        buf = BytesIO()

        spreadsheet = self.create_default_ods()

        self.generate_ods(spreadsheet, file_context).save(buf)

        return Response(
            buf.getvalue(),
            mimetype='application/vnd.oasis.opendocument.spreadsheet',
            headers={
                "Content-Disposition": (
                    "attachment;filename={}.ods"
                ).format(file_context['filename']),
                "Content-Type": "application/vnd.oasis.opendocument.spreadsheet"
            }
        ), 200

    def dispatch_request(self, **kwargs):
        response = None

        self._pre_request_hook(**kwargs)
        self._init_clients()

        file_context = self.get_file_context(**kwargs)
        file_type = self.determine_filetype()

        if file_type is None:
            abort(400)

        elif file_type == DownloadFileView.FILETYPES.CSV:
            response = self.create_csv_response(file_context)

        else:
            response = self.create_ods_response(file_context)

        self._post_request_hook(response, **kwargs)
        return response
