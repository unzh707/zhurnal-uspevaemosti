from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True удобен при разработке; для продакшена его нужно отключить.
    app.run(debug=True)
