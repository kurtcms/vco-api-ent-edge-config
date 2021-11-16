from vco_api_main import vco_api_main

class pccwg_vco(vco_api_main):
    def __init__(self):
        super().__init__()

if __name__ == '__main__':
    '''
    Create the VCO client object, and read and write the Edge
    config stacks by calling the respective functions.
    '''
    conn = pccwg_vco()
    ent_edge_config = conn.get_ent_edge_config()
    conn.write_ent_edge_config(ent_edge_config)
