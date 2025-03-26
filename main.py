
from flask import Flask, request, jsonify,render_template
import controller.data as data  
import threading
import webbrowser
from waitress import serve

app = Flask(__name__)

@app.route("/start-scraper", methods=["POST"])
def start_scraper():
    try:
        payload = request.json
        required_keys = [
            "url", "start_year", "end_year", "district_name",
            "start_number", "end_number", "first_name", "last_name"
        ]

        missing_keys = [key for key in required_keys if key not in payload]
        if missing_keys:
            return jsonify({"error": f"Missing fields: {', '.join(missing_keys)}"}), 400

        # Run scraper (blocking)
        data.change_dropdown_and_crawl(
            url=payload["url"],
            start_year_input=payload["start_year"],
            end_year_input=payload["end_year"],
            district_name_input=payload["district_name"],
            start_number_input=payload["start_number"],
            end_number_input=payload["end_number"],
            first_name_input=payload["first_name"],
            last_name_input=payload["last_name"]
        )

        return jsonify({"message": "Scraping completed successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")  
    

if __name__ == "__main__":
    threading.Timer(2.0, open_browser).start()
    print("Server starting on http://127.0.0.1:5000")
    serve(app, host="0.0.0.0", port=5000)
