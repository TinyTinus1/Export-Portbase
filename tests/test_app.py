import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import xlrd
from app import app, extract_document, export_workbook


def row(**overrides):
    return {"mrn":"26NL00000000000001","country":"GB","plate":"TEST-01","booking":"TEST-BOOKING",**overrides}

class ExportTests(unittest.TestCase):
    def test_exact_template_columns_and_literal_text(self):
        data=export_workbook([row(booking='=1+1')]).getvalue()
        book=xlrd.open_workbook(file_contents=data,formatting_info=True)
        self.assertEqual(book.sheet_names(),['Export shipments','Guide'])
        s=book.sheet_by_index(0)
        self.assertEqual([s.cell_value(2,c) for c in [0,1,4,5]],['DOCNR','DOCTYPE','TRANSPORTEQUIPMENTID','BOOKINGREF'])
        self.assertEqual([s.cell_value(3,c) for c in [0,1,4,5]],['26NL00000000000001','EU','TEST-01','=1+1'])
        self.assertEqual(s.cell_type(3,5),xlrd.XL_CELL_TEXT)
        self.assertEqual(s.cell_value(3,3),'')

    def test_destination_overrides_client_type(self):
        s=xlrd.open_workbook(file_contents=export_workbook([row(country='IE',type='EU')]).getvalue()).sheet_by_index(0)
        self.assertEqual(s.cell_value(3,1),'TT2')

    def test_required_inputs(self):
        for key in ['mrn','country','plate','booking']:
            with self.subTest(key=key),self.assertRaises(ValueError):export_workbook([row(**{key:''})])

    def test_duplicate_mrn(self):
        with self.assertRaises(ValueError):export_workbook([row(),row()])

    def test_invalid_identifiers(self):
        for changes in [{'mrn':'not-an-mrn'},{'country':'GB1'},{'plate':'x'*101}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):export_workbook([row(**changes)])

    def test_export_more_rows_than_template(self):
        docs=[row(mrn=f'26NL{i:014d}') for i in range(25)]
        s=xlrd.open_workbook(file_contents=export_workbook(docs).getvalue()).sheet_by_index(0)
        self.assertEqual(s.cell_value(27,0),docs[-1]['mrn'])

class HttpTests(unittest.TestCase):
    def setUp(self):self.client=app.test_client()
    def test_reject_external_origin(self):
        r=self.client.post('/api/export',json={'documents':[row()]},headers={'X-Portbase-Request':'local','Origin':'https://example.com'})
        self.assertEqual(r.status_code,403)
    def test_require_local_header(self):
        self.assertEqual(self.client.post('/api/export',json={'documents':[row()]}).status_code,403)
    def test_reject_wrong_host(self):
        self.assertEqual(self.client.get('/',headers={'Host':'attacker.example'}).status_code,403)
    def test_bad_pdf_and_bad_json(self):
        headers={'X-Portbase-Request':'local'}
        self.assertEqual(self.client.post('/api/extract',data=b'not a pdf',headers=headers).status_code,400)
        self.assertEqual(self.client.post('/api/export',json=[],headers=headers).status_code,400)
    def test_real_export_attachment(self):
        response=self.client.post('/api/export',json={'documents':[row()]},headers={'X-Portbase-Request':'local'})
        self.assertEqual(response.status_code,200)
        self.assertIn('Portbase-import.xls',response.headers['Content-Disposition'])
        self.assertTrue(response.data.startswith(bytes.fromhex('d0cf11e0')))
    def test_browser_download_is_single_use(self):
        response=self.client.post('/api/prepare-export',json={'documents':[row()]},headers={'X-Portbase-Request':'local'})
        self.assertEqual(response.status_code,200)
        url=response.get_json()['download_url']
        downloaded=self.client.get(url)
        self.assertEqual(downloaded.status_code,200)
        self.assertEqual(xlrd.open_workbook(file_contents=downloaded.data).sheet_by_index(0).cell_value(3,4),'TEST-01')
        self.assertEqual(self.client.get(url).status_code,404)

if __name__=='__main__':unittest.main()
