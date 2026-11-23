import unittest
from fastapi.testclient import TestClient
from server import app,Start

class HotfixTests(unittest.TestCase):
 def test_populations_available_in_ui_are_valid(self):
  for n in (24,48,80,120,192,256):
   self.assertEqual(Start(population=n).population,n)
 def test_structured_validation_errors_preserved(self):
  r=TestClient(app).post('/api/start',json={'population':999})
  self.assertEqual(r.status_code,422)
  self.assertIsInstance(r.json()['detail'],list)
  self.assertIn('population',str(r.json()['detail']))
 def test_system_endpoint_reports_available_cores(self):
  info=TestClient(app).get('/api/system').json()
  self.assertGreaterEqual(info['logical_cores'],1)
  self.assertEqual(info['population_max'],256)

if __name__=='__main__':unittest.main()
