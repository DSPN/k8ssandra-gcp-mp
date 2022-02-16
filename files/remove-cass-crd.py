import yaml

manifest_path = "/data/manifest-expanded/chart.yaml"

with open(manifest_path, "r", encoding="utf-8") as stream:
    content = stream.read()

docs = []
for d in yaml.safe_load_all(content):
    if d and "kind" in d:
        if d["metadata"]["name"] != "cassandradatacenters.cassandra.datastax.com":
            docs.append(d)

with open(manifest_path, "w", encoding='utf-8') as out:
    yaml.dump_all(docs, out, default_flow_style=False, explicit_start=True)

