import gzip
import io
import logging

import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.coordinates import get_sun, get_moon
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import ZScaleInterval

logger = logging.getLogger(__name__)

lc_gs = plt.GridSpec(3,4)
zscaler = ZScaleInterval()

def plot_lightcurve(
    obj_df, new_alert, postage_stamps=None,  **kwargs
):
    obj_df.sort_values("jd", inplace=True, ascending=False)

    fig = plt.figure()

    filter_lookup =  {1:"g", 2: "r", 3: "i"}

    if postage_stamps is not None:
        ax = fig.add_subplot(lc_gs[:,:-1])
    else:
        ax = fig.add_subplot(111)

    jd_diff = np.min(obj_df['jd'].values)


    for ii, (fid, fdf) in enumerate(obj_df.groupby("fid")):
        fdf.sort_values("jd", inplace=True, ascending=True)

        detections = fdf[ np.isfinite(fdf["magpsf"])]
        ulimits = fdf[ ~np.isfinite(fdf["magpsf"]) ]

        if len(ulimits) > 0:
            #detections = fdf.query("`tag`=='valid'")
            #ulimits = fdf.query("`tag`!='valid'")
            logger.info(f"lens {len(detections)}, {len(ulimits)}")
            ax.errorbar(
                ulimits["jd"].values - jd_diff, ulimits["diffmaglim"].values, 
                #yerr=ulimits["sigmapsf"].values, 
                ls="none", marker="v", color=f"C{ii}", mfc="none"
            )

        filter_name = filter_lookup.get(fid, None)
        label = r"$"+f"{filter_name}"+r"$" if filter_name else None

        ax.errorbar(
            detections["jd"].values - jd_diff, detections["magpsf"].values, 
            yerr=detections["sigmapsf"].values, 
            ls="none", marker="o", color=f"C{ii}",
            label=label
        )
    ax.set_xlabel("days since first alert")

        
    ax.set_ylim(ax.get_ylim()[::-1])
    ticks = ax.get_xticks()
    #labels = [Time(x, format="jd").to_value("iso", subfmt="date") for x in ticks]
    #ax.set_xticks(ticks, labels, rotation=30, ha="right")
    ax.legend()

    fig.subplots_adjust(top=0.9)
    title = f"{new_alert['objectId']}"
    for key, val in kwargs.items():
        if key.startswith("info"):
            title = title + "\n" + " ".join(f"{k}:{v}" for k, v in val.items())
    ax.text(0.5, 1.05, title, ha="center", va="bottom", transform=ax.transAxes)

    if postage_stamps is not None:

        for ii, imtype in enumerate(["Science", "Template", "Difference"]):
            im_ax = fig.add_subplot(lc_gs[ii:ii+1, -1:])

            im_ax.set_xticks([])
            im_ax.set_yticks([])
            im_ax.text(
                1.02, 0.5, imtype, rotation=90, transform=im_ax.transAxes, ha="left", va="center"
            )

            im = postage_stamps.get(imtype, None)
            if im is None:
                continue

            im_finite = im[ np.isfinite(im) ]

            vmin, vmax = zscaler.get_limits(im_finite.flatten())

            im_ax.imshow(im, vmin=vmin, vmax=vmax)

            xl_im = len(im.T)
            yl_im = len(im)
            im_ax.plot([0.5 * xl_im, 0.5 * xl_im], [0.2*yl_im, 0.4*yl_im], color="r")
            im_ax.plot([0.2*yl_im, 0.4*yl_im], [0.5*yl_im, 0.5*yl_im], color="r")
    fig.tight_layout()

    return fig

def readstamp(stamp: str, return_type='array') -> np.array:
    """ 
    copied and pasted directly from 
    https://github.com/astrolabsoftware/fink-science-portal/blob/master/apps/utils.py#L201 ...
    
    Read the stamp data inside an alert.
    Parameters
    ----------
    alert: dictionary
        dictionary containing alert data
    field: string
        Name of the stamps: cutoutScience, cutoutTemplate, cutoutDifference
    return_type: str
        Data block of HDU 0 (`array`) or original FITS uncompressed (`FITS`) as file-object.
        Default is `array`.
    Returns
    ----------
    data: np.array
        2D array containing image data (`array`) or FITS file uncompressed as file-object (`FITS`)
    """
    if stamp is None:
        logger.warn("postage stamp is none")
        return None
    with gzip.open(io.BytesIO(stamp), 'rb') as f:
        with fits.open(io.BytesIO(f.read())) as hdul:
            if return_type == 'array':
                data = hdul[0].data
            elif return_type == 'FITS':
                data = io.BytesIO()
                hdul.writeto(data)
                data.seek(0)
    return data


def plot_observing_chart(target: SkyCoord, observatory: EarthLocation, t0=None):
    if t0 is None:
        t0 = Time.now()
    time_grid = t0 + np.linspace(0, 24, 24*12) * u.hour
    #target = SkyCoord(ra=ra*u.deg, dec=dec*u.deg)
    logger.info(target)
    
    altaz_transform = AltAz(obstime=time_grid, location=observatory)
    target_altaz = target.transform_to(altaz_transform)

    moon_pos = get_moon(time_grid)
    moon_altaz = moon_pos.transform_to(altaz_transform)
    moon_dist = target.separation(SkyCoord(ra=moon_pos.ra, dec=moon_pos.dec))

    sun_pos = get_sun(time_grid)
    sun_altaz = sun_pos.transform_to(altaz_transform)
    sun_dist = target.separation(SkyCoord(ra=sun_pos.ra, dec=sun_pos.dec))

    fig, ax = plt.subplots()

    timestamps = np.array([x.timestamp() for x in time_grid.value])
    timestamp0 = timestamps[0]
    timestamps = timestamps - timestamp0

    ax.fill_between(
        timestamps, -90*u.deg, 90*u.deg, sun_altaz.alt < 0*u.deg, color="0.5", 
    )
    ax.fill_between(
        timestamps, -90*u.deg, 90*u.deg, sun_altaz.alt < -18*u.deg, color="0.2", 
    )

    ax.plot(timestamps, target_altaz.alt.deg, color="b", label="target")
    ax.plot(timestamps, moon_altaz.alt.deg, color="grey", ls="--", label="moon")
    ax.plot(timestamps, sun_altaz.alt.deg, color="grey", ls=":", label="sun")
    ax.set_ylim(0, 90)
    ax.set_ylabel("Altitude [deg]", fontsize=16)

    if all(target_altaz.alt < 30*u.deg):
        ax.text(
            0.5, 0.5, f"target alt never >30 deg", color="red", rotation=45,
            ha="center", va="center", transform=ax.transAxes, fontsize=18
        )

    obs_lat = observatory.lat.signed_dms
    obs_lon = observatory.lat.signed_dms
    lat_str = f"{round(obs_lat.d)} {round(obs_lat.m)} {round(obs_lat.s)}"
    lat_card = "W" if obs_lat.sign < 0 else "E"
    lon_str = f"{round(obs_lon.d)} {round(obs_lon.m)} {round(obs_lon.s)}"
    lon_card = "S" if obs_lon.sign < 0 else "N"
    try:
        title = f"Observing from {observatory.info.name}"
    except Exception as e:
        title = f"Observing from {lon_str} {lon_card} {lat_str} {lat_card}"
    ax.text(
        0.5, 1.0, title, fontsize=14,
        ha="center", va="bottom", transform=ax.transAxes
    )


    ax2 = ax.twinx()

    mask = target_altaz.alt > 10. * u.deg
    airmass_time = timestamps[ mask ]
    airmass = 1. / np.cos(target_altaz.zen[ mask ]).value

    
    ax2.plot(airmass_time, airmass, color="red")
    ax2.set_ylim(1.0, 4.0)
    ax2.set_ylabel("Airmass", color="red", fontsize=14)
    ax2.tick_params(axis='y', colors='red')

    xticks = ax.get_xticks()

    ax.legend()

    return fig