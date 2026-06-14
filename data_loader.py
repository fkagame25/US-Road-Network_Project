import time
from neo4j import GraphDatabase


# 1. DATABASE CONNECTION CONFIGURATION

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Password123" 

FILE_PATH = "usa (1).txt"


# 2. FILE PARSING PIPELINE

def parse_usa_file(file_path):
    print(f"[*] Reading and parsing '{file_path}'...")
    intersections = []
    roads = []
    
    with open(file_path, 'r') as f:
        # The first line specifies total nodes and edges
        first_line = f.readline().strip().split()
        num_intersections = int(first_line[0])
        num_roads = int(first_line[1])
        
        # Read Intersection Nodes (Index, X-coord, Y-coord)
        for _ in range(num_intersections):
            line = f.readline()
            if not line: break
            parts = line.strip().split()
            intersections.append({
                'id': int(parts[0]),
                'x': int(parts[1]),
                'y': int(parts[2])
            })
            
        # Read Road Edges (Source ID, Destination ID)
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                roads.append({
                    'source': int(parts[0]),
                    'target': int(parts[1])
                })
                
    print(f"[✓] Parsing complete: Found {len(intersections)} intersections and {len(roads)} roads.")
    return intersections, roads


# 3. NEO4J BATCH INGESTION LOGIC

def load_data_to_neo4j(intersections, roads):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Step A: Clear previous database entries and set performance indexes
        print("[*] Preparing database and optimization indexes...")
        session.run("MATCH (n) DETACH DELETE n")
        session.run("CREATE CONSTRAINT FOR (i:Intersection) REQUIRE i.id IS UNIQUE")
        
        # Step B: Batch Ingest Intersections
        print("[*] Ingesting Intersections in batches...")
        batch_size = 5000
        start_time = time.time()
        
        for i in range(0, len(intersections), batch_size):
            batch = intersections[i:i + batch_size]
            session.run("""
                UNWIND $batch AS data
                CREATE (i:Intersection {id: data.id, x: data.x, y: data.y})
            """, batch=batch)
        print(f"[✓] Nodes created successfully in {time.time() - start_time:.2f} seconds.")

        # Step C: Batch Ingest Roads (Edges)
        print("[*] Ingesting Roads in batches...")
        start_time = time.time()
        
        for i in range(0, len(roads), batch_size):
            batch = roads[i:i + batch_size]
            session.run("""
                UNWIND $batch AS edge
                MATCH (source:Intersection {id: edge.source})
                MATCH (target:Intersection {id: edge.target})
                CREATE (source)-[:ROAD]->(target)
            """, batch=batch)
        print(f"[✓] Relationships built successfully in {time.time() - start_time:.2f} seconds.")

    driver.close()
    print("[✓] Data loading complete!")

if __name__ == "__main__":
    try:
        nodes, edges = parse_usa_file(FILE_PATH)
        load_data_to_neo4j(nodes, edges)
    except Exception as e:
        print(f"[X] An error occurred: {e}")