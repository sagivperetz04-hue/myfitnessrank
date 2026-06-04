from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/rank', methods=['GET'])
def get_rank():
    return jsonify({
        "status": "success",
        "message": "FitRank API is running",
        "rank": "Unranked"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)