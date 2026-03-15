# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import random

def create_square(a=5.0, origin=(0,0,0), value=1, layer_name="Raster"):
    """Erzeugt ein Quadrat mit Farbe entsprechend dem Wert."""
    if not rs.IsLayer(layer_name):
        rs.AddLayer(layer_name)

    ox, oy, oz = origin
    pts = [(ox, oy, oz),
           (ox + a, oy, oz),
           (ox + a, oy + a, oz),
           (ox, oy + a, oz),
           (ox, oy, oz)]
    
    polyline_id = rs.AddPolyline(pts)
    hatch_id = rs.AddHatch(polyline_id, hatch_pattern="Solid")

    base_color = (255, 0, 0)  # Rot für 2er
    color_dict = {
        1:(0,200,0),
        2:(255,0,0),
        3:(0,0,255),
        4:(255,255,255)
    }

    if isinstance(value, float) and int(value) == 2:
        cluster_index = int(round((value - 2.0) * 10))
        r = max(0, base_color[0] - 40 * (cluster_index - 1))
        g = max(0, base_color[1] - 10 * (cluster_index - 1))
        b = max(0, base_color[2])
        color = (r, g, b)
    else:
        color = color_dict.get(value, (255,255,255))
    
    rs.ObjectColor(hatch_id, color)

    center = (ox + a/2, oy + a/2, 0)
    text_id = rs.AddTextDot(str(value), center)

    for obj in [polyline_id, hatch_id, text_id]:
        rs.ObjectLayer(obj, layer_name)
    
    return {"polyline": polyline_id, "hatch": hatch_id, "text": text_id, "value": value}


def create_single_raster(rows, cols, cell_size, layer_name, base_origin,
                         max_ones_ratio, continue_probability, neighbor_probability):
    """Erzeugt ein Raster mit allen bisherigen Regeln, beginnend bei base_origin."""

    ox0, oy0, oz0 = base_origin
    MAX_GLOBAL_ATTEMPTS = 20
    global_attempts = 0

    while global_attempts < MAX_GLOBAL_ATTEMPTS:
        values = [[0 for _ in range(cols)] for _ in range(rows)]

        # ---------- Wert 3 platzieren ----------
        count_3 = 0
        positions_3 = []
        i, j = random.randint(0, rows-1), random.randint(0, cols-1)
        values[i][j] = 3
        positions_3.append((i,j))
        count_3 += 1

        if random.randint(0,100) <= 20:
            while True:
                i2, j2 = random.randint(0, rows-1), random.randint(0, cols-1)
                if values[i2][j2] == 0:
                    values[i2][j2] = 3
                    positions_3.append((i2,j2))
                    count_3 += 1
                    break

        # ---------- Wert 4 platzieren ----------
        placed_4 = 0
        all_neighbors = []
        for (i,j) in positions_3:
            if placed_4 >= count_3:
                break
            neighbors = []
            if i > 0 and values[i-1][j]==0: neighbors.append((i-1,j))
            if i < rows-1 and values[i+1][j]==0: neighbors.append((i+1,j))
            if j > 0 and values[i][j-1]==0: neighbors.append((i,j-1))
            if j < cols-1 and values[i][j+1]==0: neighbors.append((i,j+1))
            if neighbors:
                all_neighbors.append(neighbors)
        
        pos_count = {}
        for neighbors in all_neighbors:
            for pos in neighbors:
                pos_count[pos] = pos_count.get(pos, 0) + 1
        
        duplicates = [pos for pos, cnt in pos_count.items() if cnt > 1]
        if duplicates:
            ni, nj = random.choice(duplicates)
            values[ni][nj] = 4
            placed_4 += 1
        else:
            for neighbors in all_neighbors:
                if placed_4 >= count_3:
                    break
                ni, nj = random.choice(neighbors)
                values[ni][nj] = 4
                placed_4 += 1

        # ---------- Wert 1 platzieren ----------
        def place_ones():
            edge_positions = []
            for i in range(rows):
                for j in range(cols):
                    if values[i][j] == 0:
                        if i==0 or j==0 or i==rows-1 or j==cols-1:
                            edge_positions.append((i,j))
            if not edge_positions: return
            i1,j1 = random.choice(edge_positions)
            values[i1][j1] = 1
            max_ones = int(rows*cols*max_ones_ratio)
            current_ones = 1
            active_positions = [(i1,j1)]
            while active_positions and current_ones < max_ones:
                ci,cj = random.choice(active_positions)
                neighbors = [(ci-1,cj),(ci+1,cj),(ci,cj-1),(ci,cj+1)]
                neighbors = [(ni,nj) for ni,nj in neighbors if 0<=ni<rows and 0<=nj<cols and values[ni][nj]==0]
                if not neighbors:
                    active_positions.remove((ci,cj))
                    continue
                ni,nj = random.choice(neighbors)
                values[ni][nj] = 1
                current_ones += 1
                active_positions.append((ni,nj))
                if random.random() > continue_probability:
                    break

        def is_valid_configuration(values):
            has_1_adjacent_to_4 = False
            for i in range(rows):
                for j in range(cols):
                    if values[i][j]==4:
                        valid_neighbor_found=False
                        for di,dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                            ni,nj=i+di,j+dj
                            if 0<=ni<rows and 0<=nj<cols:
                                if values[ni][nj] in (1,4):
                                    valid_neighbor_found=True
                                if values[ni][nj]==1:
                                    has_1_adjacent_to_4=True
                        if not valid_neighbor_found:
                            return False
            return has_1_adjacent_to_4

        place_ones()
        attempts = 0
        while not is_valid_configuration(values) and attempts < 100:
            for i in range(rows):
                for j in range(cols):
                    if values[i][j]==1:
                        values[i][j]=0
            place_ones()
            attempts+=1
        if not is_valid_configuration(values):
            global_attempts += 1
            continue

        # ---------- Rest = 2 ----------
        for i in range(rows):
            for j in range(cols):
                if values[i][j]==0:
                    values[i][j]=2

        # ---------- Clusterbildung ----------
        def clusterize_twos():
            cluster_index=1
            def get_neighbors(i,j):
                return [(i+di,j+dj) for di,dj in [(-1,0),(1,0),(0,-1),(0,1)]
                        if 0<=i+di<rows and 0<=j+dj<cols]
            remaining_twos=[(i,j) for i in range(rows) for j in range(cols) if values[i][j]==2]
            while remaining_twos:
                i0,j0=random.choice(remaining_twos)
                cluster_val=round(2.0+cluster_index*0.1,1)
                values[i0][j0]=cluster_val
                active_cells=[(i0,j0)]
                while active_cells:
                    ci,cj=random.choice(active_cells)
                    for ni,nj in get_neighbors(ci,cj):
                        if values[ni][nj]==2 and random.random()<neighbor_probability:
                            values[ni][nj]=cluster_val
                            active_cells.append((ni,nj))
                    active_cells.remove((ci,cj))
                cluster_index+=1
                remaining_twos=[(i,j) for i in range(rows) for j in range(cols) if values[i][j]==2]
            return [round(2.0+idx*0.1,1) for idx in range(1,cluster_index)]

        def cluster_has_neighbor_1(cluster_value):
            for i in range(rows):
                for j in range(cols):
                    if values[i][j]==cluster_value:
                        for di,dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                            ni,nj=i+di,j+dj
                            if 0<=ni<rows and 0<=nj<cols and values[ni][nj]==1:
                                return True
            return False

        def cluster_has_edge_cell(cluster_value):
            for i in range(rows):
                for j in range(cols):
                    if values[i][j]==cluster_value:
                        neighbors=[(i-1,j),(i+1,j),(i,j-1),(i,j+1)]
                        neighbors=[(ni,nj) for ni,nj in neighbors if 0<=ni<rows and 0<=nj<cols]
                        if len(neighbors)<4:
                            return True
            return False

        max_cluster_attempts=100
        cluster_attempt=0
        while cluster_attempt<max_cluster_attempts:
            cluster_values=clusterize_twos()
            if all(cluster_has_neighbor_1(cv) and cluster_has_edge_cell(cv) for cv in cluster_values):
                break
            else:
                for i in range(rows):
                    for j in range(cols):
                        if int(values[i][j])==2:
                            values[i][j]=2
                cluster_attempt+=1

        if cluster_attempt>=max_cluster_attempts:
            global_attempts+=1
            continue

        # ---------- Raster zeichnen ----------
        for i in range(rows):
            for j in range(cols):
                origin=(ox0 + j*cell_size, oy0 + i*cell_size, oz0)
                create_square(cell_size, origin, values[i][j], layer_name)

        return  # Fertig

    print("Keine gültige Rasterkonfiguration gefunden.")


def create_multiple_rasters(rows=4, cols=4, cell_size=10, layer_name="Raster",
                            max_ones_ratio=0.4, continue_probability=0.8, neighbor_probability=0.5,
                            total_rasters=6, max_fields_x=32):
    """Erzeugt mehrere Raster mit Layerüberprüfung und maximaler Feldanzahl pro Reihe."""

    # Layer überprüfen und ggf. löschen
    if rs.IsLayer(layer_name):
        existing_objects = rs.ObjectsByLayer(layer_name)
        if existing_objects:
            delete = rs.GetString(
                "Es befinden sich Objekte auf dem Layer '{}'. Sollen sie gelöscht werden?".format(layer_name),
                strings=["Ja","Nein"]
            )
            if delete == "Ja":
                rs.DeleteObjects(existing_objects)

    # Maximal Raster pro Reihe berechnen
    rasters_per_row = max_fields_x // cols
    if rasters_per_row < 1:
        rasters_per_row = 1

    for n in range(total_rasters):
        row_index = n // rasters_per_row
        col_index = n % rasters_per_row

        ox = col_index * (cols * cell_size + cell_size)  # +1 Feld Abstand
        oy = -row_index * (rows * cell_size + cell_size)  # +1 Feld Abstand

        origin = (ox, oy, 0)

        create_single_raster(rows, cols, cell_size, layer_name,
                             origin, max_ones_ratio, continue_probability, neighbor_probability)


# ------------------------
# Beispielaufruf
# ------------------------
create_multiple_rasters(
    rows=4,
    cols=4,
    cell_size=8,
    layer_name="Raster",
    max_ones_ratio=0.4,
    continue_probability=0.8,
    neighbor_probability=0.4,
    total_rasters=10,
    max_fields_x=32
)
