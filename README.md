# ThalirAI

Agri Platform - minimal skeleton

This project contains a minimal Flask skeleton for an agriculture platform with separate blueprints for auth, farmer, consumer, supplier, admin, marketplace and schemes. Templates and static placeholders are included.

To run locally:

1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. Create a `.env` file in the project root using `.env.example` as the template
5. Set any API keys you want to enable, especially `GEMINI_API_KEY` and `OPENWEATHER_API_KEY`
6. flask run
