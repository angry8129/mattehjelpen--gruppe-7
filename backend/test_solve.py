import unittest

from fastapi.testclient import TestClient

from backend import tools
from backend.main import app


class SolveEndpointTests(unittest.TestCase):
    def test_tools_can_solve_derivative_task(self) -> None:
        result = tools.solve_task("deriver x^2 + 3*x - 1", variable="x")
        self.assertTrue("2*x + 3" in result["resultat"] or "2*x + 3" in result["latex"])

    def test_solve_endpoint_handles_derivative_request(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/solve",
            json={"problem": "deriver x^2 + 3*x - 1", "variable": "x"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue("2*x + 3" in payload["resultat"] or "2*x + 3" in payload["latex"])

    def test_solve_system_endpoint(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/tools/solve_system",
            json={
                "equations": ["2*x + 3*y = 7", "x - y = 1"],
                "variables": ["x", "y"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("x: 2", response.json()["resultat"])
        self.assertIn("y: 1", response.json()["resultat"])

    def test_pythagoras_endpoint(self) -> None:
        client = TestClient(app)
        response = client.post("/tools/pythagoras", json={"side_a": 3, "side_b": 4})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resultat"], "hypotenuse = 5")

    def test_solve_endpoint_handles_system_request(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/solve",
            json={
                "problem": "løs likningssett: 2*x + 3*y = 7; x - y = 1",
                "variable": "x,y",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("x: 2", response.json()["resultat"])

    def test_solve_endpoint_allows_cors_from_frontend_origin(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/solve",
            json={"problem": "deriver x^2 + 3*x - 1", "variable": "x"},
            headers={"Origin": "http://localhost:8080"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:8080")

    def test_detailed_solve_returns_steps_formulas_and_validation(self) -> None:
        result = tools.solve_task_detailed("deriver x^2 + 3*x - 1", variable="x")
        self.assertEqual(result["resultat"], "2*x + 3")
        self.assertTrue(result["steg"])
        self.assertEqual(result["formler"][0]["formula_id"], "DER-001")
        self.assertTrue(result["validering"]["verifisert"])

    def test_detailed_ode_uses_initial_condition_and_validates(self) -> None:
        result = tools.solve_task_detailed(
            "løs differensiallikning: y' - 3*y = 6*exp(3*x), y(0)=2",
            variable="x",
        )
        self.assertIn("(6*x + 2)*exp(3*x)", result["resultat"])
        self.assertTrue(result["validering"]["verifisert"])

    def test_proof_task_is_marked_unverified(self) -> None:
        result = tools.solve_task_detailed("bevis Pythagoras' læresetning")
        self.assertFalse(result["validering"]["verifisert"])
        self.assertEqual(result["validering"]["type"], "tekstresonnement")


if __name__ == "__main__":
    unittest.main()
