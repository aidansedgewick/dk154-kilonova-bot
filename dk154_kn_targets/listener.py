import datetime
import json
import logging
import time
import traceback
import urllib
import yaml
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from telegram import Bot
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from fink_client.avroUtils import write_alert, _get_alert_schema
from fink_client.consumer import AlertConsumer

from dk154_kn_targets.fink_query import FinkQuery
from dk154_kn_targets.plotting import plot_lightcurve, readstamp, plot_observing_chart

from dk154_kn_targets import paths



logger = logging.getLogger(__name__)

_telegram_admin_path = paths.config_path / "telegram_admin.yaml"

def bot_status_update(msg, test_mode=False, loglevel="info"):
    """
    Should only be called infrequently - eg. to send messages crashe, etc!!
    """
    with open(_telegram_admin_path, "r") as f:
        telegram_admin = yaml.load(f, Loader=yaml.FullLoader)
    status_bot = Bot(token=telegram_admin['http_api'])
    if test_mode:
        sudoers = telegram_admin['test_users']
    else:
        sudoers = telegram_admin['sudoers']
    if loglevel == "error":
        logger.error(msg)
    elif loglevel == "warn" or loglevel == "warning":
        logger.warn(msg)
    else:
        logger.info(msg)
    for user in sudoers:
        status_bot.send_message(chat_id=user, text=msg)


class Listener:
    """
    The main class for the bot.

    >>> listener = Listener(<your_fink_credentials>, listener_config=<config_here>)
    >>> listener.start()

    parameters
    ----------
    credential_config
        a dict with `username`, `bootstrap.server`, `group_id` - sign up to fink-client for this.
    listener_config [optional]
        a (nested) dict. see configs for a default. currently contains
            {sleep_time: <>, consumer: {num_alerts: <IGNORED>, timeout: <>, topics: [<>, <>]}}
    """


    def __init__(self, credential_config: dict, listener_config=None, test_mode=False):
        if credential_config is None:
            raise ValueError("must provide credential config")
        self.credential_config = credential_config

        self.listener_config = listener_config or {}
        self.consumer_config = self.listener_config.get("consumer", {})
        topics = self.consumer_config.get("topics", None)
        if topics is None:
            topics = ['fink_kn_candidates_ztf']
        self.topics = topics
        self.sleep_time = self.listener_config.get("sleep_time", 60)
    
        with open(_telegram_admin_path, "r") as f:
            telegram_admin = yaml.load(f, Loader=yaml.FullLoader)
        self.token = telegram_admin['http_api']
        self.bot = Bot(token=self.token)
        self.telegram_sudoers = telegram_admin['sudoers']
        self.test_users = telegram_admin['test_users']
        self.api_url = "https://api.telegram.org"
        self.responded = []
        
        self.datestamp = datetime.datetime.now().strftime("%Y%m%d")
        self.test_mode = test_mode
        test_mode_file = paths.base_path / "test_mode"
        if test_mode_file.exists():
            self.test_mode = True
        if self.test_mode:
            logger.info("YOU ARE IN TEST MODE")

        self.observatories = [
            EarthLocation.of_site("La Silla Observatory")
        ]


    def listen_for_alerts(self,):
        num_alerts = self.consumer_config.get("num_alerts", 1)
        timeout = self.consumer_config.get("timeout", 5)
        logger.info(f"listening for {timeout} sec...")
        with AlertConsumer(self.topics, self.credential_config) as consumer:
            # Context manager so no consumer.close()

            # consume not working for topics other than sso?? use poll for now...
            ## latest_alerts = consumer.consume(num_alerts=num_alerts, timeout=timeout)
            topic, alert, key = consumer.poll(timeout=timeout)
            if any([x is None for x in [topic, alert, key]]):
                return []
            else:
                latest_alerts = [(topic, alert, key, )]
        return latest_alerts


    def dump_alert(self, topic, alert, key, outdir=None):
        _parsed_schema = _get_alert_schema(key=key) # ??? - copied from fink-client scripts...
        if outdir is None:
            outdir = paths.alertDB_path
        write_alert(alert, _parsed_schema, outdir, overwrite=True)


    def process_alerts(self, latest_alerts, **kwargs):

        logger.info(f"{len(latest_alerts)} new alerts!")
        for topic, alert, key in latest_alerts:
            
            self.dump_alert(topic, alert, key)
            new_alert = alert["candidate"]
            

            extra_keys = [
                'candid', 'objectId', 'timestamp', 'cdsxmatch', 
                'rf_snia_vs_nonia', 'snn_snia_vs_nonia', 'snn_sn_vs_all', 
                'mulens', 'roid', 'nalerthist', 'rf_kn_vs_nonkn'
            ] 
            new_alert.update({k: alert[k] for k in extra_keys} )

            alert_history = pd.DataFrame(alert["prv_candidates"])
            if len(alert_history) == 0:
                continue
            if any([x is None for x in alert_history["magpsf"]]):
                prv_candidates = pd.DataFrame(alert["prv_candidates"])
                logger.info("launch query")
                alert_history = FinkQuery.query_objects(
                    objectId=alert["objectId"], return_df=True
                )
                column_lookup = {
                    col: col.split(":")[1] if ":" in col else col for col in alert_history.columns
                }
                alert_history.rename(column_lookup, axis=1, inplace=True)

            alert_history.append(new_alert, ignore_index=True)

            postage_stamps = {
                imtype: readstamp(alert.get('cutout'+imtype, {}).get('stampData', None)) 
                for imtype in FinkQuery.imtypes
            }

            fig, fig_path = self.plot_lightcurve(
                alert_history, new_alert, postage_stamps=postage_stamps,
                info1=dict(
                    kn_prob=f"{new_alert['rf_kn_vs_nonkn']:.2f}", 
                    sn_prob=f"{new_alert['snn_sn_vs_all']:.2f}"
                )
            )
            plt.close(fig)

            observing_charts = []
            for observatory in self.observatories:
                oc_fig, oc_fig_path = self.plot_observing_chart(new_alert, observatory)
                plt.close(oc_fig)
                observing_charts.append(oc_fig_path)
            
            alert_timestamp = Time(new_alert['jd'], format="jd").to_value("iso")
            msg = (
                f"New {topic} alert!\n"
                f"{alert_timestamp}\n"
                f"{new_alert['objectId']}\n"
                f"at ra={new_alert['ra']:.5f}, dec={new_alert['dec']:.4f}\n"
                f"magnitude {new_alert['magpsf']:.2f}\n"
                f"{len(alert_history)} alerts total "
                f"({sum(~np.isfinite(alert_history['magpsf']))} bad/limits)"
            )

            self.update_users(
                texts=msg, fig_paths=[fig_path] + observing_charts
            )


    def plot_lightcurve(self, lc_data, new_alert, postage_stamps, **kwargs):
        logger.info("plotting lightcurve")
        fig = plot_lightcurve(lc_data, new_alert, postage_stamps=postage_stamps, **kwargs)
        fig_dir = paths.alertDB_path / f"lc_plots/{self.datestamp}"
        fig_dir.mkdir(exist_ok=True, parents=True)
        fig_path = fig_dir / f"{new_alert['objectId']}.png"
        ii = 0
        while fig_path.exists():
            fig_path = fig_dir / f"{new_alert['objectId']}_{ii}.png"
            ii = ii + 1
        try:
            print_path = fig_path.relative_to(paths.base_path)
        except:
            print_path = fig_path
        logger.info(f"save lc to {print_path}")
        fig.savefig(fig_path)
        return fig, fig_path


    def plot_observing_chart(self, new_alert, observatory: EarthLocation):
        logger.info("plot observing charts")
        target = SkyCoord(ra=new_alert["ra"], dec=new_alert["dec"], unit="deg")
        fig = plot_observing_chart(target, observatory)
        fig_dir = paths.alertDB_path / f"oc_plots/{self.datestamp}"
        fig_dir.mkdir(exist_ok=True, parents=True)

        try:
            suffix = observatory.info.name
        except:
            obs_lat = observatory.lat.signed_dms
            obs_lon = observatory.lat.signed_dms
            lat_str = f"{round(obs_lat.d)} {round(obs_lat.m)} {round(obs_lat.s)}"
            lat_card = "W" if obs_lat.sign < 0 else "E"
            lon_str = f"{round(obs_lon.d)} {round(obs_lon.m)} {round(obs_lon.s)}"
            lon_card = "S" if obs_lon.sign < 0 else "N"
            suffix = f"Observing from {lon_str} {lon_card} {lat_str} {lat_card}"
        
        suffix = suffix.replace(" ", "_")
        fig_path = fig_dir / f"{new_alert['objectId']}_{suffix}.png"
        ii = 0
        while fig_path.exists():
            fig_path = fig_path = fig_dir / f"{new_alert['objectId']}_{suffix}_{ii}.png"
            ii = ii + 1
        try:
            print_path = fig_path.relative_to(paths.base_path)
        except:
            print_path = fig_path
        fig.savefig(fig_path)
        logger.info(f"save lc to {print_path}")
        return fig, fig_path


    def send_to_user(self, chat_id, texts=None, fig_paths=None):
        if texts is None:
            texts = []
        if isinstance(texts, str):
            texts = [texts]
        if fig_paths is None:
            fig_paths = []
        if isinstance(fig_paths, (str, Path)):
            figs = [fig_paths]

        for text in texts:
            self.bot.send_message(chat_id=chat_id, text=text)
        for fig_path in fig_paths:
            with open(fig_path, "rb") as fig:
                self.bot.send_photo(chat_id=chat_id, photo=fig)
        

    def update_users(self, texts=None, fig_paths=None):
        telegram_users_path = paths.config_path / "telegram_users.yaml"
        with open(telegram_users_path, "r") as f:
            telegram_users = yaml.load(f, Loader=yaml.FullLoader)
        if self.test_mode:
            telegram_users = self.test_users
        

        for user in telegram_users:
            user_errors = []
            try:
                self.send_to_user(user, texts=texts, fig_paths=fig_paths)
            except Exception as e:
                tr = traceback.format_exc()
                print(tr)
                print(e)
                user_errors.append(user)
            if len(user_errors) > 0:
                msg = f"sudo report: \nerror updating {len(user_errors)} users\n(bot still running)"
                bot_status_update(msg, test_mode=self.test_mode, loglevel="warn")

    def listen_for_user_updates(self,):
        raise NotImplementedError

        updates = urllib.request.urlopen(
            self.api_url+f"/bot{self.token}/getUpdates"
        )
        messages =  json.loads(updates.read().decode())["result"]
        return messages

    def respond_to_user_updates(self, updates):
        raise NotImplementedError

        telegram_users_path = paths.config_path / "telegram_users.yaml"
        with open(telegram_users_path, "r") as f:
            telegram_users = yaml.load(f, Loader=yaml.FullLoader)
        for update in updates:
            message = update.get('message', None)
            if message is None:
                continue
            print(message)
            user_id = message['from']['id']
            if user_id != 240295980:
                print("not user id")
                continue
            text = message.get('text', None)
            if text is None:
                continue

            if text == "/start":
                self.send_to_user(chat_id=user_id, texts="do /status, /subscribe, /unsubscribe")
            elif text == "/subscribe":
                if user_id in telegram_users:
                    self.send_to_user(chat_id=user_id, texts="you're already subscribed!")
                else:
                    self.send_to_user(chat_id=user_id, texts="thanks for subscribing! :)")
            elif text == "/status":
                self.send_to_user(chat_id=user_id, texts="I'm alive!")
                


    def start(self):
        while True:
            logger.info(f"sleep for {self.sleep_time} sec...")
            time.sleep(self.sleep_time)
            self.datestamp = datetime.datetime.now().strftime("%Y%m%d")
            latest_alerts = self.listen_for_alerts()
            if len(latest_alerts) == 0:
                continue
            self.process_alerts(latest_alerts)
            #updates = self.listen_for_user_updates()
            #self.respond_to_user_updates(updates)
