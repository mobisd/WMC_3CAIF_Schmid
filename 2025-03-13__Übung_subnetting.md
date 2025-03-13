**Subnetting Übungsprotokoll**

---

## Übung 1
### Aufgabe:
Bilde aus dem Netz 192.168.0.0 /24 4 Subnetze. Netze mit Mindestzahl an nutzbaren Host aber nicht darunter wählen: Netz a mit 20, Netz b mit 15, Netz c mit 30, und das Netz d mit den Rest Anteil der Netzwerkadressen.

### **Antwort:**
- Netz A
  - Netzwerkadresse: 192.168.0.0 /27
  - Broadcastadresse: 192.168.0.31
  - Nutzbare Hosts: 192.168.0.1 - 192.168.0.30

- Netz B
  - Netzwerkadresse: 192.168.0.32 /28
  - Broadcastadresse: 192.168.0.47
  - Nutzbare Hosts: 192.168.0.33 - 192.168.0.46

- Netz C 
  - Netzwerkadresse: 192.168.0.48 /27
  - Broadcastadresse: 192.168.0.79
  - Nutzbare Hosts: 192.168.0.49 - 192.168.0.78

- Netz D
  - Netzwerkadresse: 192.168.0.80 /26
  - Broadcastadresse: 92.168.0.143
  - Nutzbare Hosts: 192.168.0.81 - 192.168.0.142

---

## Übung 2
### Aufgabe:
Teile das Netz 193.170.20.0 /24 in 8 gleich große Subnetze.

### **Antwort:**
- Jedes Subnetz hat eine Subnetzmaske von 255.255.255.224.
- Die Netzwerkadressen sind: 193.170.20.0, 193.170.20.32, 193.170.20.64, 193.170.20.96, 193.170.20.128, 193.170.20.160, 193.170.20.192, 193.170.20.224.
- Jedes Subnetz hat 30 nutzbare Hosts, und die Broadcastadresse endet jeweils 31 Adressen weiter.

---

## Übung 3
### Aufgabe:
Teile 172.28.40.0 /26 in zwei Subnetze.

### **Antwort:**
- Erstes Subnetz: 172.28.40.0 /27 → Nutzbare Hosts: 172.28.40.1 - 172.28.40.30, Broadcast: 172.28.40.31
- Zweites Subnetz: 172.28.40.32 /27 → Nutzbare Hosts: 172.28.40.33 - 172.28.40.62, Broadcast: 172.28.40.63

---

## Übung 4
### Aufgabe:
Subnetzmaske für 17.0.0.0 mit 10 Subnetzen und mindestens 12 Hosts.

### **Antwort:**
- Da mindestens 12 Hosts je Subnetz benötigt werden, werden mindestens 14 Adressen benötigt.
- Ein /28-Netz hat 16 Adressen, was ausreicht.
- Um 10 Subnetze zu erhalten, ist eine Subnetzmaske von 255.255.255.240 erforderlich.

---

## Übung 5
### Aufgabe:
Bestimme die Subnetzmaske für 210.52.190.0 mit 5 Subnetzen und mindestens 10 Hosts.

### **Antwort:**
- Da mindestens 12 Adressen pro Subnetz benötigt werden, passt ein /28-Netz mit 16 Adressen.
- Die Subnetzmaske ist daher 255.255.255.240.

---

## Übung 6
### Aufgabe:
Wozu werden /30 Netze verwendet?

### Antwort:
- Ein /30-Netz hat nur 4 Adressen, wovon 2 nutzbar sind.
- Solche Netze werden für Point-to-Point-Verbindungen zwischen Routern genutzt.

---

## Übung 7
### Aufgabe:
Netz- und Hostanteil der Klassen A, B und C.

### **Antwort:**
- **Klasse A**: Netzwerkanteil: 8 Bit, Hostanteil: 24 Bit
- **Klasse B**: Netzwerkanteil: 16 Bit, Hostanteil: 16 Bit
- **Klasse C**: Netzwerkanteil: 24 Bit, Hostanteil: 8 Bit

---

### Quellen:
- https://www.subnet-calculator.com/

