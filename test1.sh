cp -r ~/text2sql_react/* .
rm -rf logs
rm -rf uploads
rm -rf chromadb_data
rm -rf chroma_data
rm -rf backup_milvus
rm -rf tmp
find . -type f -name "*.pyc" | xargs rm

