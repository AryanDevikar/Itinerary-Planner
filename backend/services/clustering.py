import numpy as np
from sklearn.cluster import KMeans
from typing import List


def cluster_venues(venues: List[dict], n_clusters: int = None) -> List[List[dict]]:
    """Group venues geographically into clusters using k-means on lat/lng."""
    if not venues:
        return []

    n = min(n_clusters or 2, len(venues))

    # Guard: if fewer venues than clusters, just return one cluster
    if len(venues) <= n:
        return [venues]

    coords = np.array([[v["lat"], v["lng"]] for v in venues])
    labels = KMeans(n_clusters=n, random_state=42, n_init=10).fit_predict(coords)

    clusters = {}
    for i, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(venues[i])

    return list(clusters.values())


def order_cluster_by_distance(cluster: List[dict]) -> List[dict]:
    """Greedy nearest-neighbor ordering within a cluster using haversine distance."""
    if len(cluster) <= 1:
        return cluster

    remaining = cluster.copy()
    ordered   = [remaining.pop(0)]

    while remaining:
        last = ordered[-1]
        distances = [
            _haversine(last["lat"], last["lng"], v["lat"], v["lng"])
            for v in remaining
        ]
        nearest_idx = int(np.argmin(distances))
        ordered.append(remaining.pop(nearest_idx))

    return ordered


def build_itinerary(venues: List[dict], max_stops: int = 4, n_clusters: int = 2) -> List[dict]:
    """
    Top-level function: cluster venues, order each cluster,
    then pick the best stops up to max_stops.
    Returns a flat ordered list of stops.
    """
    clusters  = cluster_venues(venues, n_clusters=n_clusters)
    itinerary = []

    for cluster in clusters:
        ordered = order_cluster_by_distance(cluster)
        itinerary.extend(ordered)

    # Trim to max_stops, keeping highest-rated first within the ordered list
    return itinerary[:max_stops]


def _haversine(lat1, lng1, lat2, lng2) -> float:
    """Straight-line distance in km between two lat/lng points."""
    R    = 6371
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi    = np.radians(lat2 - lat1)
    dlambda = np.radians(lng2 - lng1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))