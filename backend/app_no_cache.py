from app import create_app
app = create_app()
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
