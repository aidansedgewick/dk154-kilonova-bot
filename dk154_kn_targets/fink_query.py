import logging
import requests
import time

import numpy as np
import pandas as pd

logger = logging.getLogger("fink_query")

class FinkQueryError(Exception):
    pass

class FinkQuery:
    """See https://fink-portal.org/api"""


    fink_latests_url = 'https://fink-portal.org/api/v1/latests'
    fink_objects_url = 'https://fink-portal.org/api/v1/objects'
    fink_explorer_url = 'https://fink-portal.org/api/v1/explorer'
    fink_cutout_url = 'https://fink-portal.org/api/v1/cutouts'

    imtypes = ("Science", "Template", "Difference")

    def __init__(self):
        pass

    @classmethod
    def query_latest_alerts(cls, return_df=True, **kwargs):
        t0 = time.time()
        req = requests.post(cls.fink_latests_url, json=kwargs)
        t1 = time.time()
        logger.info(f"query_latest status {req.status_code}")
        if req.status_code in [404, 500, 504]:
            logger.error("\033[31;1merror rasied\033[0m")
            if t1-t0 > 58.:
                logger.error("likely a timeout error")
            raise FinkQueryError(req.content.decode())
        if not return_df:
            return req
        return pd.read_json(req.content)

    @classmethod
    def query_objects(cls, return_df=True, **kwargs):
        t0 = time.time()
        req = requests.post(cls.fink_objects_url, json=kwargs)
        t1 = time.time()
        logger.info(f"query_object status {req.status_code}")
        if req.status_code in [400, 404, 500, 504]:
            logger.error("\033[31;1merror rasied\033[0m")
            if t1-t0 > 59.:
                logger.error("likely a timeout error")
            raise FinkQueryError(req.content.decode())
        if not return_df:
            return req
        return pd.read_json(req.content)

    @classmethod
    def query_database(cls, return_df=True, **kwargs):
        t0 = time.time()
        req = requests.post(cls.fink_explorer_url, json=kwargs)
        t1 = time.time()
        logger.info(f"query_object status {req.status_code}")
        if req.status_code in [404, 500, 504]:
            logger.error("\033[31;1merror rasied\033[0m")
            if t1-t0 > 59.:
                logger.error("likely a timeout error")
            logger.error("error rasied")
            raise FinkQueryError(req.content.decode())
        if not return_df:
            return req
        return pd.read_json(req.content)

    @classmethod
    def get_cutout(cls, imtype, **kwargs):
        if imtype not in cls.imtypes:
            raise ValueError(f"choose imtype from {cls.imtypes}")
        imtype_key = 'b:cutout'+imtype+'_stampData' # gives eg 'b:cutoutScience_stampData'

        json_data = {
            'kind': imtype,
            'output-format': 'array',
        }
        json_data.update(kwargs)
        im_req = requests.post(
            cls.fink_cutout_url, json=json_data
        )
        try:
            im_df = pd.read_json(im_req.content)
        except Exception as e:
            logger.warn(f"on request for {imtype} stamp: {e}")
            return None

        try:
            im = np.array(im_df[imtype_key].values[0], dtype=float)
        except:
            logger.warn(f"on request for {imtype} stamp: {e}")
            return None

        return im
            
        


