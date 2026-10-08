import unittest
import asyncio
from backend.tools.calc import CalculatorTool
from backend.pipeline.router import intent_router
from backend.platform.discovery import tool_discovery
from backend.tools.python_executor import python_executor_tool

class TestEngineImprovements(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.calc = CalculatorTool()

    async def test_word_problem_discounts(self):
        # 1. Standard English discount
        res1 = await self.calc.execute(expression="If a product costs $80 and has a 15% discount, what is the final price?")
        self.assertTrue(res1.success)
        self.assertIn("$68", str(res1.data))

        # 2. Variant format
        res2 = await self.calc.execute(expression="Product costs 120$ with a 20% discount")
        self.assertTrue(res2.success)
        self.assertIn("$96", str(res2.data))

        # 3. Khmer discount
        res3 = await self.calc.execute(expression="បញ្ចុះតម្លៃ 15% លើ 80 ដុល្លារ")
        self.assertTrue(res3.success)
        self.assertIn("$68", str(res3.data))

    async def test_word_problem_geometry(self):
        # 1. Rectangle area
        res1 = await self.calc.execute(expression="A rectangle has a length of 12 cm and a width of 5 cm. Calculate its area.")
        self.assertTrue(res1.success)
        self.assertIn("60", str(res1.data))

        # 2. Khmer rectangle area
        res2 = await self.calc.execute(expression="ចតុកោណកែង បណ្តោយ 12 cm និង ទទឹង 5 cm គណនាផ្ទៃក្រឡា")
        self.assertTrue(res2.success)
        self.assertIn("60", str(res2.data))

        # 3. Triangle area
        res3 = await self.calc.execute(expression="triangle base 10 and height 4")
        self.assertTrue(res3.success)
        self.assertIn("20", str(res3.data))

        # 4. Circle area
        res4 = await self.calc.execute(expression="circle with radius 7 area")
        self.assertTrue(res4.success)
        self.assertIn("153.94", str(res4.data))

    def test_runnable_code_extractor(self):
        prompt = (
            "Trace the output:\n\n"
            "python\n\n"
            "x = 10\n"
            "y = 5\n\n"
            "if x > y:\n"
            "    print(\"A\")\n"
            "else:\n"
            "    print(\"B\")\n"
            "What will be printed?"
        )
        extracted = intent_router._extract_runnable_code(prompt)
        self.assertIn("x = 10", extracted)
        self.assertIn("print(\"A\")", extracted)
        self.assertNotIn("Trace the output", extracted)
        self.assertNotIn("What will be printed", extracted)

    def test_code_tracing_intent_routing(self):
        prompt = (
            "Trace the output:\n"
            "x = 10\n"
            "y = 5\n"
            "if x > y:\n"
            "    print(\"A\")\n"
            "else:\n"
            "    print(\"B\")"
        )
        intent, allowed = intent_router.classify_intent(prompt)
        tool, args = intent_router.route(prompt)

        self.assertIn("python_execute", allowed)
        self.assertEqual(tool, "python_execute")
        self.assertIn("x = 10", args.get("code", ""))
        self.assertIn("print(\"A\")", args.get("code", ""))

    def test_khmer_code_tracing_routing(self):
        prompt = "តើកូដនេះ print អ្វីចេញមក?\nx = 10\nprint(x * 2)"
        intent, allowed = intent_router.classify_intent(prompt)
        tool, args = intent_router.route(prompt)

        self.assertIn("python_execute", allowed)
        self.assertEqual(tool, "python_execute")
        self.assertIn("x = 10", args.get("code", ""))

    def test_khmer_math_discovery(self):
        tools = tool_discovery.discover_tools("គណនាបញ្ចុះតម្លៃ 15% លើ 80 ដុល្លារ")
        tool_names = [t.name for t in tools]
        self.assertIn("calculator", tool_names)

        tools_geom = tool_discovery.discover_tools("គណនាផ្ទៃក្រឡាចតុកោណកែង បណ្តោយ 12 ទទឹង 5")
        geom_names = [t.name for t in tools_geom]
        self.assertIn("calculator", geom_names)

    async def test_question_11_sandbox_execution(self):
        # Verify Question 11 prints 'A' and NEVER 'B'
        code = "x = 10\ny = 5\nif x > y:\n    print(\"A\")\nelse:\n    print(\"B\")"
        res = await python_executor_tool.execute(code=code)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("stdout"), "A")

    async def test_question_12_sandbox_execution(self):
        # Verify Question 12 (range 1 to 6) sum = 15
        code = "total = 0\nfor i in range(1, 6):\n    total += i\nprint(total)"
        res = await python_executor_tool.execute(code=code)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("stdout"), "15")

if __name__ == "__main__":
    unittest.main()
