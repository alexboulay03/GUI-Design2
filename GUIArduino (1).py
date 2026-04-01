import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time

arduino = None
is_acquiring = False
latest_reading = "0.0"

# Valeurs gains regulateurs
anciennes_valeurs_pid = {
    "KpPos": None,
    "KiPos": None,
    "KdPos": None,
    "KpCour": None,
    "KiCour": None
}

#connexion arduino
def get_available_ports():
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    return port_list if port_list else ["Aucun port"]

def connect_serial():
    global arduino
    selected_port = port_combobox.get()
    selected_baud = int(baudrate_combobox.get())
    
    if selected_port == "Aucun port":
        status_label.configure(text="Erreur: Aucun port trouvé", text_color="#e74c3c")
        return

    if arduino and arduino.is_open:
        arduino.close()

    try:
        arduino = serial.Serial(selected_port, selected_baud, timeout=1)
        status_label.configure(text=f"Connecté: {selected_port} à {selected_baud}", text_color="#3498db")
    except serial.SerialException:
        status_label.configure(text=f"Erreur: Impossible d'ouvrir {selected_port}", text_color="#e74c3c")
        arduino = None

#reception serie
def read_serial_data():
    global is_acquiring
    while is_acquiring and arduino and arduino.is_open:
        try:
            if arduino.in_waiting > 0:
                raw_data = arduino.readline().decode('utf-8').strip()
                if raw_data:
                    # On separe a chaque virgule
                    valeurs = raw_data.split(',')
                    
                    #  si 3 valeurs (coefficicents polynome)
                    if len(valeurs) == 3:
                        try:
                            valeur_x2 = float(valeurs[0])
                            valeur_x = float(valeurs[1])
                            valeur_y = float(valeurs[2])
                            app.after(0, update_cal_display, valeur_x2, valeur_x, valeur_y)
                        except ValueError:
                            print(f"Erreur de conversion (Calibration) : {raw_data}")
                            
                    # 1 valeur (Poid)
                    elif len(valeurs) == 1:
                        app.after(0, update_data_display, raw_data)

            time.sleep(0.01) 

        except serial.SerialException:
            print("Connexion série interrompue")
            is_acquiring = False
            break
        except Exception as e:
            print(f"Erreur de lecture{e}")
            time.sleep(0.1)


def update_data_display(data):
    global latest_reading
    latest_reading = data
    
    try:
        valeur_en_grammes = float(data)
        unite_actuelle = menu_unite.get()
        valeur_convertie = convertir_poids(valeur_en_grammes, unite_actuelle)
        data_label.configure(text=f"{valeur_convertie:.1f} {unite_actuelle}")
    except ValueError:
        print(f"Erreur de lecture")

#Acquisition
def start_acquisition():
    global is_acquiring
    if not arduino or not arduino.is_open:
        status_label.configure(text="Erreur: Non connecté", text_color="#e74c3c")
        return
    if not is_acquiring:
        is_acquiring = True 
        threading.Thread(target=read_serial_data, daemon=True).start()
        status_label.configure(text="Status: Acquisition en cours", text_color="#2ecc71")
        app.after(1000, executer_cal_et_tare)

def executer_cal_et_tare():
    if is_acquiring and arduino and arduino.is_open:
        app.after(500, tare)

def convertir_poids(valeur_g, unite_cible):
    if unite_cible == "oz":
        return valeur_g * 0.03527396
    elif unite_cible == "N":
        return (valeur_g / 1000.0) * 9.80665
    else:
        return valeur_g

def tare():
    global latest_reading
    if arduino and arduino.is_open:
        arduino.write(f"Tare:{latest_reading}\n".encode('utf-8'))
        status_label.configure(text="Status: Tare effectuée", text_color="#2ecc71")
    else:
        status_label.configure(text="Erreur: Non connecté", text_color="#e74c3c")

# Changement mode
def change_mode(choice):
    normal_frame.pack_forget()
    setup_frame.pack_forget()
    Cal_frame.pack_forget()
    if choice == "Mode Normal":
        setup_frame.pack_forget()
        Cal_frame.pack_forget()
        normal_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Setup":
        setup_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Calibration":
        Cal_frame.pack(fill="both", expand=True, pady=10)

def save_setup():
    """Exemple de fonction pour le mode Setup"""
    cal_value = cal_entry.get()
    print(f"Sauvegarde de la calibration: {cal_value}")
    # Vous pourriez envoyer ça à l'Arduino ici : arduino.write(f"CAL:{cal_value}\n".encode('utf-8'))

def SetPID():
    global anciennes_valeurs_pid
    nouvelles_valeurs = {
        "KpPos": KpPos_entry.get(),
        "KiPos": KiPos_entry.get(),
        "KdPos": KdPos_entry.get(),
        "KpCour": KpCour_entry.get(),
        "KiCour": KiCour_entry.get()
    }
    
    #compare les nouvelles et anciennes valeurs
    for parametre, valeur_lue in nouvelles_valeurs.items():
        if valeur_lue.strip() != "": 
            # Si different, on envoie les nouvelles
            if valeur_lue != anciennes_valeurs_pid[parametre]:
                message = f"{parametre}:{valeur_lue}\n"
                if arduino and arduino.is_open:
                    arduino.write(message.encode('utf-8'))
                    print(f"Mise à jour envoyée : {message.strip()}")
                anciennes_valeurs_pid[parametre] = valeur_lue


def Cal(poid):
    message = f"Cal:{poid}\n"
    if arduino and arduino.is_open:
        arduino.write(message.encode('utf-8'))
        print(f"Mise à jour envoyée : {message.strip()}")
        if poid == 200:
            app.after(500, tare)


# GUI
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.geometry("900x700") 
app.title("Arduino GUI")

top_frame = ctk.CTkFrame(app)
top_frame.pack(pady=10, padx=20, fill="x")

port_combobox = ctk.CTkComboBox(top_frame, values=get_available_ports(), width=100)
port_combobox.grid(row=0, column=0, padx=10, pady=10)

baudrate_combobox = ctk.CTkComboBox(top_frame, values=["9600", "115200"], width=90)
baudrate_combobox.grid(row=0, column=1, padx=10, pady=10)
baudrate_combobox.set("115200")

btn_connect = ctk.CTkButton(top_frame, text="Connecter", command=connect_serial, width=90)
btn_connect.grid(row=0, column=2, padx=10, pady=10)

mode_label = ctk.CTkLabel(top_frame, text="Vue:")
mode_label.grid(row=0, column=3, padx=(20, 5), pady=10)

mode_combobox = ctk.CTkComboBox(top_frame, values=["Mode Normal", "Mode Setup", "Mode Calibration"], command=change_mode, width=120)
mode_combobox.grid(row=0, column=4, padx=5, pady=10)

status_label = ctk.CTkLabel(app, text="Status: En attente de connexion", font=("Roboto", 14))
status_label.pack(pady=5)

content_frame = ctk.CTkFrame(app, fg_color="transparent")
content_frame.pack(fill="both", expand=True, padx=20, pady=10)


# Mode Normal
normal_frame = ctk.CTkFrame(content_frame, fg_color="transparent")

instruction_acquisition = ctk.CTkLabel(
    normal_frame,
    text="Cliquez sur 'Connecter' et puis sur 'Acquisition'." \
    " Pour débuter la prise de mesure,\n"
    " déposez la masse au centre de la cible.",
    font=("Roboto", 20, "bold")
)
instruction_acquisition.pack(pady=(10, 20))

data_label = ctk.CTkLabel(normal_frame, text="---", font=("Roboto", 48, "bold"))
data_label.pack(pady=30)

btn_start = ctk.CTkButton(normal_frame, text="Acquisition", command=start_acquisition, fg_color="#27ae60", hover_color="#2ecc71")
btn_start.pack(pady=10)

btn_tare = ctk.CTkButton(normal_frame, text="Tare", command=tare, fg_color="#27ae60", hover_color="#2ecc71")
btn_tare.pack(pady=5)

normal_frame.pack(fill="both", expand=True)


#Mode setup
setup_frame = ctk.CTkFrame(content_frame)

setup_title = ctk.CTkLabel(setup_frame, text="Définir les gains de chaque régulateur", font=("Roboto", 20, "bold"))
setup_title.pack(pady=20)

KpPos_label = ctk.CTkLabel(setup_frame, text="Kp Position:")
KpPos_label.pack(pady=5)

KpPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.15")
KpPos_entry.pack(pady=5)

KiPos_label = ctk.CTkLabel(setup_frame, text="Ki Position:")
KiPos_label.pack(pady=5)

KiPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="2.3")
KiPos_entry.pack(pady=5)

KdPos_label = ctk.CTkLabel(setup_frame, text="Kd Position:")
KdPos_label.pack(pady=5)

KdPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.02")
KdPos_entry.pack(pady=5)

KpCour_label = ctk.CTkLabel(setup_frame, text="Kp Courant:")
KpCour_label.pack(pady=5)

KpCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.25")
KpCour_entry.pack(pady=5)

KiCour_label = ctk.CTkLabel(setup_frame, text="Ki Courant:")
KiCour_label.pack(pady=5)

KiCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="2.4")
KiCour_entry.pack(pady=5)

btn_Set = ctk.CTkButton(setup_frame, text="Envoyer", command=SetPID)
btn_Set.pack(pady=20)

# Mode Calibration
Cal_frame = ctk.CTkFrame(content_frame)

Calib_label = ctk.CTkLabel(Cal_frame, text="---", font=("Roboto", 48, "bold"))
Calib_label.pack(pady=30)

def update_cal_display(valeur_x2, valeur_x, valeur_c):
    signe_x = "+" if valeur_x >= 0 else "-"
    signe_c = "+" if valeur_c >= 0 else "-"
    polynome_str = f"{valeur_x2:.2f}X² {signe_x} {abs(valeur_x):.2f}X {signe_c} {abs(valeur_c):.2f}"
    Calib_label.configure(text=polynome_str)


valeurs_poids = ["0", "20", "40", "60", "80", "100"]
instruction_calibration = ctk.CTkLabel(
    Cal_frame,
    text = "Pour calibrer, déposez une masse puis enregistrez le point en indiquant la valeur de cette masse. " \
    ""\
    "Cliquez sur 'Envoyer' une fois que tous les points sont enregistrés. Une fois envoyé, " \
    "retirer les masses de la balance",
    font=("Roboto", 15, "bold"),
    wraplength=500,
    justify="center"
)
instruction_calibration.pack(pady=(10, 20))

def envoyer_poids_selectionne():
    selection = menu_poids.get()
    poids_brut = selection.replace(" ✓", "")
    Cal(int(poids_brut))
    for i in range(len(valeurs_poids)):
        if valeurs_poids[i].replace(" ✓", "") == poids_brut:
            valeurs_poids[i] = f"{poids_brut} ✓"
            
    menu_poids.configure(values=valeurs_poids)
    menu_poids.set(f"{poids_brut} ✓")


# Calibration
menu_poids = ctk.CTkOptionMenu(Cal_frame, values=valeurs_poids, width=150)
menu_poids.pack(pady=15)
menu_poids.set("0")

btn_Envoyer_Poids = ctk.CTkButton(Cal_frame, text="Envoyer la masse sélectionnée", command=envoyer_poids_selectionne, fg_color="#3498db", hover_color="#2980b9")
btn_Envoyer_Poids.pack(pady=10)

separation = ctk.CTkFrame(Cal_frame, height=2, width=200, fg_color="gray")
separation.pack(pady=15)


def envoyer_calibration():
    valeurs_attendues = ["0 ✓", "20 ✓", "40 ✓", "60 ✓", "80 ✓", "100 ✓"]
    
    if all(valeur in valeurs_poids for valeur in valeurs_attendues):
        Cal(200)
        status_label.configure(text="Status: Calibration effectuée", text_color="#2ecc71")
        app.after(1000, executer_cal_et_tare)
    else:
        status_label.configure(text="Erreur: Il manque une mesure de masse", text_color="#e74c3c")

btn_Done = ctk.CTkButton(
    Cal_frame,
    text="Envoyer (Terminer)",
    command=envoyer_calibration,
    fg_color="#27ae60",
    hover_color="#2ecc71"
)
btn_Done.pack(pady=10)


def on_unite_change(nouvelle_unite):
    """Met à jour l'affichage immédiatement quand on change d'unité via le menu."""
    global latest_reading
    try:
        valeur_en_grammes = float(latest_reading)
        valeur_convertie = convertir_poids(valeur_en_grammes, nouvelle_unite)
        data_label.configure(text=f"{valeur_convertie:.1f} {nouvelle_unite}")
    except ValueError:
        pass

# Changement unite
unites_disponibles = ["g", "oz", "N"]
menu_unite = ctk.CTkOptionMenu(
    normal_frame, 
    values=unites_disponibles, 
    width=150, 
    command=on_unite_change
)
menu_unite.pack(pady=15)
menu_unite.set("g")


def on_closing():
    global is_acquiring
    is_acquiring = False
    if arduino and arduino.is_open:
        arduino.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()