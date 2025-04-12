cp -r ~/text2sql/* .
find . -type d -name __pycache__ | xargs rm -rf
rm logs/*
rm uploads/*
