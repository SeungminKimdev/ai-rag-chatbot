import os
import ollama

folder_path = "./data"
file_list = os.listdir(folder_path)
chunks = []
chunks_size = 500
overlap = 100
step = chunks_size - overlap

for file_name in file_list:
    if not file_name.endswith(".md"):
        continue
    print(file_name)
    
    file_path = folder_path + "/" + file_name
    with open(file_path, "r", encoding="utf-8") as fd:
        data = fd.read()
        
        for i in range(0, len(data), step):
            chunks.append({"filename":file_name, "content":data[i:i+chunks_size]})

for chunk in chunks:
    response = ollama.embed(model="bge-m3", input=chunk["content"])
    chunk["embedding"] = response["embeddings"][0]

print(len(chunks))                    # 청크 개수
print(len(chunks[0]["embedding"]))    # 첫 청크의 벡터 길이 → 1024