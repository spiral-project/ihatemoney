from flask import Blueprint
from flask_cors import CORS
from flask_restful import Api

from ihatemoney.api.common import (
    BillHandler,
    BillsHandler,
    CurrenciesHandler,
    MemberHandler,
    MembersHandler,
    ProjectHandler,
    ProjectsHandler,
    ProjectStatsHandler,
    TokenHandler,
)

api = Blueprint("api", __name__, url_prefix="/api")
CORS(api)
restful_api = Api(api)

restful_api.add_resource(CurrenciesHandler, "/currencies")
restful_api.add_resource(ProjectsHandler, "/projects")
restful_api.add_resource(ProjectHandler, "/projects/<string:project_id>")
restful_api.add_resource(TokenHandler, "/projects/<string:project_id>/token")
restful_api.add_resource(MembersHandler, "/projects/<string:project_id>/members")
restful_api.add_resource(
    ProjectStatsHandler, "/projects/<string:project_id>/statistics"
)
restful_api.add_resource(
    MemberHandler, "/projects/<string:project_id>/members/<int:member_id>"
)
restful_api.add_resource(BillsHandler, "/projects/<string:project_id>/bills")
restful_api.add_resource(
    BillHandler, "/projects/<string:project_id>/bills/<int:bill_id>"
)
