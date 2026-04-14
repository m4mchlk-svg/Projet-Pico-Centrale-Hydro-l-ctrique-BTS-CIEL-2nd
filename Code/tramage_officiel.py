def checkup_syst(nv_eau,nv_vanne,syst,meteo): 
    #il faut regarder si tout fonctionne bien
    # 0x0000:RAS / 0x0001:i2c / 0x0002:moteur / 0x0004:capteur 1 / 0x0008:capteur 2 / 0x0010:...
    # 0%0000 -> 1er bit pour i2c , 2eme pour moteur , ...
    return checkup #du type 0x0006 donc 0%0110 donc pb moteur et capteur 1

def checkup_meteo(var):
    meteo = 0x00
    if crue:
        meteo 0xFF
    
    return meteo #du type 0xFF ou 0x00

def get_trame(nv_eau, nv_vanne, syst, meteo, crc16 ):
    """ $00#00#00#0#crc16"""
    
    return "$"+ nv_eau + "#" + nv_vanne + "#" + syst + "#" + meteo + "#" + crc16
    
    