import matplotlib.pyplot as plt

citing_points = [[1, 8040],
    [2, 17029],
    [3, 26015],
    [4, 34107],
    [5, 41737],
    [12, 95850],
    [24, 183272],
    [36, 263978],
    [48, 337697],
    [60, 406602]
    ]
cited_points = [[1, 135698],
    [2, 250352],
    [3, 348184],
    [4, 430786],
    [5, 501614],
    [12, 882215],
    [24, 1289252],
    [36, 1558873],
    [48, 1750657],
    [60, 1896332]
    ]

all_citing = 966203
all_cited = 2412432

x = [tup[0] for tup in citing_points]
citing_y = [tup[1]/all_citing for tup in citing_points]
cited_y = [tup[1]/all_cited for tup in cited_points]

plt.plot(x, citing_y)
plt.plot(x, cited_y)

plt.legend(['citing docs', 'cited docs'], loc='upper left')
plt.xlabel('last _ months of citing docs')
plt.ylabel('ratio of full data set')
plt.grid(color='lightgray', linestyle='--', linewidth=0.5)

plt.show()
