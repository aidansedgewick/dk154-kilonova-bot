import logging
import socket
import traceback
import yaml


from dk154_kn_targets.listener import Listener, bot_status_update

from dk154_kn_targets import paths




_credential_config_path = paths.config_path / "fink_credentials.yaml"
listener_config_path = paths.config_path / "alert_polling.yaml"

if __name__ == "__main__":

    logger = logging.getLogger(__file__)

    paths.config_check()

    if not _credential_config_path.exists():
        raise FileNotFoundError(
            f"add 'by hand' the fink-client credentials to:\n   {_credential_config_path}"
        )
    with open(_credential_config_path, "r") as f:
        _credential_config = yaml.load(f, Loader=yaml.FullLoader)


    if listener_config_path.exists():
        with open(listener_config_path, "r") as f:
            listener_config = yaml.load(f, Loader=yaml.FullLoader)
    else:
        poll_config = None
        logger.warn("no alert_poll.yaml - use defaults...")


    listener = Listener(_credential_config, listener_config=listener_config)
    try:
        bot_status_update(f"sudo report: starting bot on {socket.gethostname()}", loglevel="info")
        listener.start()
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):

            tr = traceback.format_exc()
            msg = (
                f"sudo report: CRASH!\n\n"
                f"full traceback:\n{tr}\n"
                f"{type(e).__name__}\n    {e}"
            )
            bot_status_update(msg, loglevel="error")