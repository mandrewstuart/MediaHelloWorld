YOUR_API_KEY_HERE = ''
SEARCH_TERM_HERE = ''


import json
import requests
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer as tfidf
import hdbscan

print('imported libraies, connecting to DB')

con = sqlite3.connect('/root/db.file')
cur = con.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS data (title text, story text, uuid text, published text, cluster_index integer)')

print('connected to DB, pulling data')

data_from_site = requests.get("https://webhose.io/search?token=YOUR_API_KEY_HERE&format=json&q=SEARCH_TERM_HERE%20language%3A(english)%20(site_type%3Anews)&latest=true")
posts = data_from_site.json()['posts']


print(len(posts))

print('data pulled, upserting into DB')

for p in posts:
    if(cur.execute("SELECT COUNT(*) FROM data WHERE uuid = ?;", [p['uuid']]).fetchall()[0][0]==0):
        cur.execute("INSERT INTO data (title, story, uuid, published, cluster_index) VALUES (?, ?, ?, ?, NULL);", [p['title'], p['text'], p['uuid'], p['published']])


print('upserted, preparing to cluster')

posts_from_db = cur.execute("SELECT uuid, story FROM data;").fetchall()
texts = [x[1] for x in posts_from_db]


vectors = tfidf(stop_words='english').fit_transform(texts)
clusterer = hdbscan.HDBSCAN(min_cluster_size=2)

print('clustering prepped, now clustering')

clusterer.fit(vectors)

clusters = list(set(clusterer.labels_))

print(str(len(set(clusterer.labels_))-1) + " clusters found")
print(str(len([x for x in clusterer.labels_ if x == -1])) + " unclustered articles present")

print("clustered, passing data back into DB")

for i in range(len(clusterer.labels_)):
    cur.execute("UPDATE data SET cluster_index = " + str(clusterer.labels_[i]) + " WHERE uuid = '" + posts_from_db[i][0] + "';")


print("get list of most recent articles to display per cluster or lonely article")

data = cur.execute("SELECT * FROM data ORDER BY published DESC;").fetchall()

data = [list(d) for d in data]

clusters = []
articles = []
c = 1
for d in data:
    if(len(articles) < 100):
        try:
            #if solo:
            if(d[-1]==-1):
                d[-1] = str(-c)
                clusters.append(str(-c))
                c = c + 1
                articles.append([d])
            else:
                i = clusters.index(d[-1])
                articles[i].append(d)
        except:
            clusters.append(d[-1])
            articles.append([d])


html = '<html><head><title>News Stories</title></head><body><h1>' + SEARCH_TERM_HERE + ' Stories</h1><h3><a href="https://action.aclu.org/secure/donate-to-aclu">Donate to the ACLU</a></h3><p>This updates hourly, pulling news from an aggregator, it clusters all previous stories, then regenerates the cache of stories, clustered so that you can stay on top of ' + SEARCH_TERM_HERE + ' Stories without having to read everything everywhere.</p><ol>'
html += '<li>' + '</li><li>'.join([('('+str(len(a))+') ' + a[0][1]) for a in articles]) + '</li>'
html += '</body></html>'

f = open('/root/custom_static.py','w')
f.write('data = """'+html+ '"""')
f.close()

con.commit()
print('DONE')
