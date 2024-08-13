# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Registration non-party validator tests."""
import copy

from flask import current_app
import pytest
# from registry_schemas import utils as schema_utils

from doc_api.utils import request_validator as validator
from doc_api.utils.logging import logger
from doc_api.models import utils as model_utils
from doc_api.models.type_tables import DocumentTypes, RequestTypes, DocumentClasses
from doc_api.resources.request_info import RequestInfo


# test data pattern is ({description}, {valid}, {req_type}, {doc_type}, {content_type}, {doc_class}, {message_content})
TEST_DATA_ADD = [
    ('Valid', True, RequestTypes.ADD, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF, DocumentClasses.CORP, None),
    ('Valid no class', True, RequestTypes.ADD, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF, None, None),
    ('Invalid missing doc type', False, RequestTypes.ADD, None, model_utils.CONTENT_TYPE_PDF, DocumentClasses.CORP,
     validator.MISSING_DOC_TYPE),
    ('Invalid doc type', False, RequestTypes.ADD, 'JUNK', model_utils.CONTENT_TYPE_PDF, DocumentClasses.CORP,
     validator.INVALID_DOC_TYPE),
    ('Invalid doc class', False, RequestTypes.ADD, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF, 'JUNK',
     validator.INVALID_DOC_CLASS),
    ('Invalid missing content', False, RequestTypes.ADD, DocumentTypes.CORP_MISC, None, DocumentClasses.CORP,
      validator.MISSING_CONTENT_TYPE),
    ('Invalid content', False, RequestTypes.ADD, DocumentTypes.CORP_MISC, 'XXXXX', DocumentClasses.CORP,
     validator.INVALID_CONTENT_TYPE),
    ('Invalid doc class - type', False, RequestTypes.ADD, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF,
     DocumentClasses.FIRM, validator.INVALID_DOC_CLASS_TYPE)
]
# test data pattern is ({description}, {valid}, {scan_date}, {filing_date}, {message_content})
TEST_DATA_ADD_DATES = [
    ('Valid no dates', True, None, None, None),
    ('Valid scan date', True, '2024-07-31', None, None),
    ('Valid filing date', True, None, '2024-07-31', None),
    ('Invalid scan date', False, 'January 12, 2022', None, validator.INVALID_SCAN_DATE),
    ('Invalid filing date', False, None, 'January 12, 2022', validator.INVALID_FILING_DATE)
]
# test data pattern is ({description}, {valid}, {doc_class}, {doc_service_id}, {doc_id}, {cons_id}, {start}, {end}, {message_content})
TEST_DATA_GET = [
    ('Valid service id', True, DocumentClasses.CORP, '1234', None, None, None, None, None),
    ('Valid doc id', True, DocumentClasses.CORP, None, '1234', None, None, None, None),
    ('Valid consumer id', True, DocumentClasses.CORP, None, None, '1234', None, None, None),
    ('Valid query dates', True, DocumentClasses.CORP, None, None, None, '2024-07-01', '2024-07-01', None),
    ('Invalid doc class', False, 'XXXX', None, None, None, None, None, validator.INVALID_DOC_CLASS),
    ('Missing doc class', False, None, '1234', None, None, None, None, validator.MISSING_DOC_CLASS),
    ('Missing params', False, DocumentClasses.CORP, None, None, None, None, None, validator.MISSING_QUERY_PARAMS),
    ('Invalid query dates', False, DocumentClasses.CORP, None, None, None, '2024-07-01', None,
     validator.MISSING_DATE_PARAM),
    ('Invalid query dates', False, DocumentClasses.CORP, None, None, None, None, '2024-07-01',
     validator.MISSING_DATE_PARAM)
]
# test data pattern is ({description}, {valid}, {start_date}, {end_date}, {message_content})
TEST_DATA_SEARCH_DATES = [
    ('Valid no dates', True, None, None, None),
    ('Valid date range', True, '2024-07-31', '2024-07-31', None),
    ('Invalid date range', False, '2024-07-31', '2024-07-30', validator.INVALID_START_END_DATE),
    ('Invalid start date', False, 'January 12, 2022', None, validator.INVALID_START_DATE),
    ('Invalid end date', False, None, 'January 12, 2022', validator.INVALID_END_DATE)
]
# test data pattern is ({description},{valid},{doc_id},{cons_id},{filename},{scan_date},{filing_date},{message_content})
TEST_DATA_PATCH = [
    ('Valid doc id', True, '89999999', None, None, None, None, None),
    ('Valid consumer id', True, None, 'BC0700000', None, None, None, None),
    ('Valid filename', True, None, None, 'change_address.pdf', None, None, None),
    ('Valid scan date', True, None, None, None, '2024-07-31', None, None),
    ('Valid filing date', True, None, None, None, None, '2024-07-31', None),
    ('Invalid no change', False, None, None, None, None, None, validator.MISSING_PATCH_PARAMS),
    ('Invalid scan date', False, None, None, None, 'January 12, 2022', None, validator.INVALID_SCAN_DATE),
    ('Invalid filing date', False, None, None, None, None, 'January 12, 2022', validator.INVALID_FILING_DATE)
]
# test data pattern is ({description}, {valid}, {payload}, {doc_type}, {content_type}, {doc_class}, {message_content})
TEST_DATA_REPLACE = [
    ('Valid', True, True, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF, DocumentClasses.CORP, None),
    ('Invalid missing content', False, True, DocumentTypes.CORP_MISC, None, DocumentClasses.CORP,
      validator.MISSING_CONTENT_TYPE),
    ('Invalid content', False, True, DocumentTypes.CORP_MISC, '*/*', DocumentClasses.CORP,
     validator.INVALID_CONTENT_TYPE),
    ('Missing payload', False, False, DocumentTypes.CORP_MISC, model_utils.CONTENT_TYPE_PDF,
     DocumentClasses.FIRM, validator.MISSING_PAYLOAD)
]


@pytest.mark.parametrize('desc,valid,start_date,end_date,message_content', TEST_DATA_SEARCH_DATES)
def test_validate_search_dates(session, desc, valid, start_date, end_date, message_content):
    """Assert that new get request validation works as expected for scan and file dates."""
    # setup
    info: RequestInfo = RequestInfo(RequestTypes.GET, 'NA', None, 'NA')
    info.account_id = 'NA'
    info.document_class = DocumentClasses.CORP
    if start_date:
        info.query_start_date = start_date
    if end_date:
        info.query_end_date = end_date
    if desc == 'Valid no dates':
        info.document_service_id = '12343'

    error_msg = validator.validate_request(info)

    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid date range':
                err_msg = validator.INVALID_START_END_DATE.format(start_date=start_date, end_date=end_date)
            elif desc == 'Invalid start date':
                err_msg = validator.INVALID_START_DATE.format(param_date=start_date)
            elif desc == 'Invalid end date':
                err_msg = validator.INVALID_END_DATE.format(param_date=end_date)
            assert error_msg.find(err_msg) != -1


@pytest.mark.parametrize('desc,valid,scan_date,filing_date,message_content', TEST_DATA_ADD_DATES)
def test_validate_add_dates(session, desc, valid, scan_date, filing_date, message_content):
    """Assert that new add request validation works as expected for scan and file dates."""
    # setup
    info: RequestInfo = RequestInfo(RequestTypes.ADD, 'NA', DocumentTypes.CORP_MISC, 'NA')
    info.content_type = model_utils.CONTENT_TYPE_PDF
    info.account_id = 'NA'
    info.document_class = DocumentClasses.CORP
    if scan_date:
        info.consumer_scandate = scan_date
    if filing_date:
        info.consumer_filedate = filing_date
    error_msg = validator.validate_request(info)
    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid scan date':
                err_msg = validator.INVALID_SCAN_DATE.format(param_date=scan_date)
            elif desc == 'Invalid filing date':
                err_msg = validator.INVALID_FILING_DATE.format(param_date=scan_date)
            assert error_msg.find(err_msg) != -1


@pytest.mark.parametrize('desc,valid,doc_class,service_id,doc_id,cons_id,start,end,message_content', TEST_DATA_GET)
def test_validate_get(session, desc, valid, doc_class, service_id, doc_id, cons_id, start, end, message_content):
    """Assert that get documents request validation works as expected."""
    # setup
    info: RequestInfo = RequestInfo(RequestTypes.GET.value, 'NA', None, 'NA')
    info.account_id = 'NA'
    if doc_class:
        info.document_class = doc_class
    if service_id:
        info.document_service_id = service_id
    if doc_id:
        info.consumer_doc_id = doc_id
    if cons_id:
        info.consumer_identifier = cons_id
    if start:
        info.query_start_date = start
    if end:
        info.query_end_date = end
    
    error_msg = validator.validate_request(info)
    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid doc class':
                err_msg = validator.INVALID_DOC_CLASS.format(doc_class=doc_class)
            assert error_msg.find(err_msg) != -1


@pytest.mark.parametrize('desc,valid,req_type,doc_type,content_type,doc_class,message_content', TEST_DATA_ADD)
def test_validate_add(session, desc, valid, req_type, doc_type, content_type, doc_class, message_content):
    """Assert that new add request validation works as expected."""
    # setup
    info: RequestInfo = RequestInfo(req_type, 'NA', doc_type, 'NA')
    info.content_type = content_type
    info.account_id = 'NA'
    if doc_class:
        info.document_class = doc_class
    error_msg = validator.validate_request(info)
    if doc_type and not doc_class and not message_content:
        assert info.document_class
        if doc_type ==  DocumentTypes.CORP_MISC:
            assert info.document_class == DocumentClasses.CORP.value
    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid doc type':
                err_msg = validator.INVALID_DOC_TYPE.format(doc_type=doc_type)
            elif desc == 'Invalid doc class':
                err_msg = validator.INVALID_DOC_CLASS.format(doc_class=doc_class)
            elif desc == 'Invalid content':
                err_msg = validator.INVALID_CONTENT_TYPE.format(content_type=content_type)
            elif desc == 'Invalid doc class - type':
                err_msg = validator.INVALID_DOC_CLASS_TYPE.format(doc_class=doc_class, doc_type=doc_type)
            assert error_msg.find(err_msg) != -1


@pytest.mark.parametrize('desc,valid,doc_id,cons_id,filename,scan_date,filing_date,message_content', TEST_DATA_PATCH)
def test_validate_patch(session, desc, valid, doc_id, cons_id, filename, scan_date, filing_date, message_content):
    """Assert that patch request validation works as expected."""
    # setup
    info: RequestInfo = RequestInfo(RequestTypes.UPDATE, 'NA', DocumentTypes.CORP_MISC, 'NA')
    info.content_type = model_utils.CONTENT_TYPE_PDF
    info.account_id = 'NA'
    info.document_class = DocumentClasses.CORP
    if doc_id:
        info.consumer_doc_id = doc_id
    if cons_id:
        info.consumer_identifier = cons_id
    if filename:
        info.consumer_filename= filename
    if scan_date:
        info.consumer_scandate = scan_date
    if filing_date:
        info.consumer_filedate = filing_date
    error_msg = validator.validate_request(info)
    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid scan date':
                err_msg = validator.INVALID_SCAN_DATE.format(param_date=scan_date)
            elif desc == 'Invalid filing date':
                err_msg = validator.INVALID_FILING_DATE.format(param_date=scan_date)
            assert error_msg.find(err_msg) != -1


@pytest.mark.parametrize('desc,valid,has_payload,doc_type,content_type,doc_class,message_content', TEST_DATA_REPLACE)
def test_validate_replace(session, desc, valid, has_payload, doc_type, content_type, doc_class, message_content):
    """Assert that new put add/replace document request validation works as expected."""
    # setup
    info: RequestInfo = RequestInfo(RequestTypes.REPLACE, 'NA', doc_type, 'NA')
    info.content_type = content_type
    info.account_id = 'NA'
    info.has_payload = has_payload
    info.document_class = doc_class
    error_msg = validator.validate_request(info)
    if doc_type and not doc_class and not message_content:
        assert info.document_class
        if doc_type ==  DocumentTypes.CORP_MISC:
            assert info.document_class == DocumentClasses.CORP.value
    if valid:
        assert error_msg == ''
    else:
        assert error_msg != ''
        if message_content:
            err_msg:str = message_content
            if desc == 'Invalid content':
                err_msg = validator.INVALID_CONTENT_TYPE.format(content_type=content_type)
            assert error_msg.find(err_msg) != -1
