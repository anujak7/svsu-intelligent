import json
import sys

def parse_glb(file_path):
    with open(file_path, "rb") as f:
        magic = f.read(4)
        if magic != b'glTF':
            print("Not a valid GLB file")
            return
        version = int.from_bytes(f.read(4), 'little')
        length = int.from_bytes(f.read(4), 'little')
        chunk_length = int.from_bytes(f.read(4), 'little')
        chunk_type = f.read(4)
        if chunk_type != b'JSON':
            print("No JSON chunk")
            return
        json_data = f.read(chunk_length).decode('utf-8')
        doc = json.loads(json_data)
        
        animations = doc.get('animations', [])
        print("Animations found:")
        for i, anim in enumerate(animations):
            print(f"{i}: {anim.get('name', 'unnamed')}")
        
        nodes = doc.get('nodes', [])
        print("\nNodes found:")
        for i, node in enumerate(nodes):
            if 'name' in node and ('Head' in node['name'] or 'Jaw' in node['name'] or 'mixamorig' in node['name']):
                print(f"{i}: {node['name']}")
                
parse_glb("assets/models/avatar.glb")
