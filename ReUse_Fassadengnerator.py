# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import random

# -------------------------------------------------------------------------
# QUADRAT ZEICHNEN
# -------------------------------------------------------------------------
def create_square(a=5.0, origin=(0,0,0), value=1, layer_name="Raster"):
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

    base_color = (255, 0, 0)
    color_dict = {
        1:(0,200,0),
        2:(255,0,0),
        3:(0,0,255),
        4:(255,200,0)
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

# -------------------------------------------------------------------------
# EIN RASTER GENERIEREN
# -------------------------------------------------------------------------
def create_single_raster(rows, cols, cell_size, layer_name, base_origin,
                         max_ones_ratio, continue_probability, neighbor_probability,
                         reset_cells):
    ox0, oy0, oz0 = base_origin
    MAX_GLOBAL_ATTEMPTS = 20
    global_attempts = 0

    while global_attempts < MAX_GLOBAL_ATTEMPTS:
        values = [[0 for _ in range(cols)] for _ in range(rows)]

        # WERT 3 platzieren
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

        # WERT 4 platzieren
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

        # WERT 1 platzieren
        def place_ones():
            edge_positions = []
            for i in range(rows):
                for j in range(cols):
                    if values[i][j] == 0:
                        if i==0 or j==0 or i==rows-1 or j==cols-1:
                            edge_positions.append((i,j))
            if not edge_positions:
                return
            i1,j1 = random.choice(edge_positions)
            values[i1][j1] = 1
            max_ones = int(rows*cols*max_ones_ratio)
            current_ones = 1
            active_positions = [(i1,j1)]
            while active_positions and current_ones < max_ones:
                ci,cj = random.choice(active_positions)
                neighbors = [(ci-1,cj),(ci+1,cj),(ci,cj-1),(ci,cj+1)]
                neighbors = [(ni,nj) for ni,nj in neighbors
                            if 0<=ni<rows and 0<=nj<cols and values[ni][nj]==0]
                if not neighbors:
                    active_positions.remove((ci,cj))
                    continue
                ni,nj = random.choice(neighbors)
                values[ni][nj] = 1
                current_ones += 1
                active_positions.append((ni,nj))
                if random.random() > continue_probability:
                    break

        # KONFIGURATION VALIDIEREN
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

        # REST: WERT 2
        for i in range(rows):
            for j in range(cols):
                if values[i][j]==0:
                    values[i][j]=2

        # CLUSTERBILDUNG
        def clusterize_twos():
            cluster_index=1
            def get_neighbors(i,j):
                return [(i+di,j+dj) for di,dj in
                        [(-1,0),(1,0),(0,-1),(0,1)]
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

        max_cluster_attempts=100
        cluster_attempt=0
        while cluster_attempt<max_cluster_attempts:
            cluster_values=clusterize_twos()
            if all(cluster_has_neighbor_1(cv) for cv in cluster_values):
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

        if reset_cells:
            for (ri, rj) in reset_cells:
                if 0 <= ri < rows and 0 <= rj < cols:
                    values[ri][rj] = 0

        return values

    print("Keine gültige Rasterkonfiguration gefunden.")
    return None

# -------------------------------------------------------------------------
# MEHRERE RASTER ERZEUGEN UND MATERIALZUWEISUNG
# -------------------------------------------------------------------------
def create_multiple_rasters(
    rows=4, cols=4, cell_size=10, layer_name="Raster",
    max_ones_ratio=0.4, continue_probability=0.8, neighbor_probability=0.5,
    total_rasters=6, max_fields_x=32,
    reset_cells=None,
    material_1=0, material_2=0, material_3=0, material_4=0, material_5=0,
    material_6=0, material_7=0, material_8=0, material_9=0, material_10=0):

    if reset_cells is None:
        reset_cells = []

    if rs.IsLayer(layer_name):
        existing_objects = rs.ObjectsByLayer(layer_name)
        if existing_objects:
            delete = rs.GetString(
                "Es befinden sich Objekte auf dem Layer '"+layer_name+"'. Sollen sie gelöscht werden?",
                strings=["Ja","Nein"]
            )
            if delete == "Ja":
                rs.DeleteObjects(existing_objects)

    rasters_per_row = max_fields_x // cols
    if rasters_per_row < 1:
        rasters_per_row = 1

    all_rasters_values = []
    all_cell_centers = []

    for n in range(total_rasters):
        row_index = n // rasters_per_row
        col_index = n % rasters_per_row
        ox = col_index * (cols * cell_size) #+ cell_size)
        oy = -row_index * (rows * cell_size) #+ cell_size)
        origin = (ox, oy, 0)
        raster_values = create_single_raster(
            rows, cols, cell_size, layer_name,
            origin,
            max_ones_ratio, continue_probability, neighbor_probability,
            reset_cells
        )
        if raster_values:
            all_rasters_values.append((raster_values, origin))

    for raster_values, origin in all_rasters_values:
        ox0, oy0, oz0 = origin
        for i in range(rows):
            for j in range(cols):
                cell_value = raster_values[i][j]
                cell_origin = (ox0 + j*cell_size, oy0 + i*cell_size, oz0)

                sq = create_square(cell_size, cell_origin, cell_value, layer_name)

                cx = cell_origin[0] + cell_size/2
                cy = cell_origin[1] + cell_size/2
                cz = 0
                all_cell_centers.append((cell_value, (cx,cy,cz)))

    area_per_cell = cell_size * cell_size / 10000.0
    total_counts = {}
    for raster_values, _ in all_rasters_values:
        for row in raster_values:
            for val in row:
                if val == 0: continue
                total_counts[val] = total_counts.get(val, 0) + 1

    print("\nGesamtflächen aller Raster:")
    for key in sorted(total_counts.keys()):
        area = total_counts[key] * area_per_cell
        print("  Wert {0}: {1:.2f} m²".format(key, float(area)))

    sorted_values_by_area = sorted(total_counts.items(), key=lambda x: x[1]*area_per_cell, reverse=True)
    print("\nZellenwerte sortiert nach Fläche:")
    for val, count in sorted_values_by_area:
        print("  Wert {0}: {1:.2f} m²".format(val, float(count*area_per_cell)))

    materials = [
        (1, material_1), (2, material_2), (3, material_3), (4, material_4), 
        (5, material_5), (6, material_6), (7, material_7), (8, material_8),
        (9, material_9), (10, material_10)
    ]
    materials_nonzero = [m for m in materials if m[1] > 0]
    materials_sorted = sorted(materials_nonzero, key=lambda x: x[1], reverse=True)

    print("\nMaterialien sortiert nach Menge:")
    for mat, qty in materials_sorted:
        print("  Material {0}: {1:.2f} m²".format(mat, float(qty)))

    assigned_material_for_value = {}
    remaining_materials = materials_sorted[:]
    not_enough_material = False

    # MATERIAL ZUWEISEN
    for val, count in sorted_values_by_area:
        cell_area = count * area_per_cell
        assigned = False
        print("\nPrüfung Wert {0}: {1:.2f} m²".format(val, float(cell_area)))
        for i, (mat, qty) in enumerate(remaining_materials):
            diff = qty - cell_area
            print("  Mit Material {0}: {1:.2f} m² verfügbar, Differenz: {2:.2f}".format(mat, float(qty), float(diff)))
            if diff >= 0:
                remaining_materials[i] = (mat, diff)
                assigned_material_for_value[val] = mat
                assigned = True
                print("  -> Zuordnung gültig")
                break
            else:
                print("  -> NICHT gültig")
        if not assigned:
            assigned_material_for_value[val] = None
            not_enough_material = True
            print("  !!! Kein Material für Wert {0}".format(val))

    print("\nRestmenge pro Material:")
    for mat, qty in remaining_materials:
        print("  Material {0}: {1:.2f} m²".format(mat, float(qty)))

    # ---------------------------------------------------------------------
    # HIER: MATERIALTEXT M1, M2 ... AUF LAYER "Raster" SCHREIBEN
    # ---------------------------------------------------------------------
    if not not_enough_material:
        print("\nSchreibe Materialzuordnung auf Zellen ...")
        for val, (x,y,z) in all_cell_centers:
            if val == 0:
                continue
            mat = assigned_material_for_value.get(val)
            text_id = rs.AddText("M"+str(mat), (x, y, z), height=0.35)
            rs.ObjectLayer(text_id, layer_name)  # ← hinzugefügt
    else:
        print("\n############################")
        print("###   ZU WENIG MATERIAL   ###")
        print("############################\n")


# -------------------------------------------------------------------------
# BEISPIELAUFRUF
# -------------------------------------------------------------------------
create_multiple_rasters(
    rows=3,
    cols=3,
    cell_size=41,
    layer_name="Raster",
    max_ones_ratio=0.1,
    continue_probability=0.8,
    neighbor_probability=0.4,
    total_rasters=330,
    max_fields_x=33,
    reset_cells=[(0,0), (0,1), (1,0), (1,1)],
    material_1=200,
    material_2=70,
    material_3=30,
    material_4=0,
    material_5=0,
    material_6=0,
    material_7=0,
    material_8=0,
    material_9=0,
    material_10=0
)
