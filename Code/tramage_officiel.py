def checkup_syst(flag_cpt1, flag_cpt2, flag_moteur):
    #0x00 -> vert -> système parfait
    #0x0[1-F] -> orange -> sytème endommager a verifier mais en état de fonctionnement
    #0x1[1-F] -> rouge -> système endommager a réparer et non fonctionnel
    """faire le dico du systeme avec key (id) 

    return code_erreur

def checkup_meteo(var):
    meteo = 0x00
    if crue:
        meteo 0xFF
    
    return meteo #du type 0xFF ou 0x00

def get_trame(nv_eau, nv_vanne, syst, meteo, crc16 ):
    """ $00#00#00#00#crc16"""
    
    return "$"+ nv_eau + "#" + nv_vanne + "#" + syst + "#" + meteo + "#" + crc16
    
    
