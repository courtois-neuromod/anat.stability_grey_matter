# Figure caption — `fig_anat_stability.svg`

Hand-written companion to the hand-authored montage, kept beside it. Every
number below was read from `stability_per_region.tsv`, `volume_trajectories.tsv`
and the per-subject `volume_trajectories_subject.tsv` on 2026-10-05; if the
pipeline is rerun on different data, re-check them before reusing this text.

---

**Figure. Grey matter volume is highly stable within each individual across
years of repeated scanning, with a small, consistent decline.** Grey matter
volumes were taken from the longitudinal FreeSurfer stream for 6 CNeuroMod
participants (5 to 15 anatomical sessions each; 76 sessions in total): 68
Desikan cortical regions (surface-based grey matter volume), 14 subcortical
structures and the 2 cerebellar cortices (partial-volume-corrected `aseg`
volumes), 84 regions in all. Each cortical region is assigned to the Yeo-7
network covering most of its voxels in native space (Schaefer 1000/7); the
volume is always that of the whole region, never split between networks.

**(A) Network key.** Nine sagittal glass brains show the extent of each
network in the MNI group atlas, stacked from most to least stable (median
within-subject coefficient of variation over regions, panel D). Their colours
are used for that network throughout the figure. The maps are for orientation
only: the analysed Desikan regions exist only in each participant's native
space.

**(B) Volume declines in every network.** Grey matter volume per session as
percent deviation from each participant's own mean for that region, averaged
over the regions of a network, then over participants. The x axis is session
order: acquisition dates are not available, so no time interval is implied.
Only sessions reached by at least 5 participants are shown (sessions 1–13).
Between the first and the thirteenth session, volume falls by 1.0 (subcortex)
to 3.1 (Cont) percentage points, e.g. from +1.45% to −1.16% in Default.

**(C) … and in every participant.** The same deviation per participant,
averaged over all 84 regions, with each participant's least-squares line (thick).
Every slope is negative, from −0.10 (sub-01) to −0.21 (sub-03, sub-04) % per
session. Across the 54 participant x network trajectories, 52 decline; the two
exceptions (DorsAttn and subcortex, +0.04 and +0.03 % per session) are both
from sub-04, who has only 5 sessions. The design cannot separate the causes of
this decline (ageing, scanner, processing), so we report its size and
consistency only.

**(D) Within- vs between-subject variation, by network.** Coefficient of
variation of regional volume across sessions within a participant, averaged over
participants (green), and across participants (orange; computed on each
participant's mean volume), with bars at the median over the network's regions
and each region overlaid as a dot. Within-subject variation is far below between-subject variation in every
one of the 84 regions: overall median 1.4% against 11.7%. Medians per network
range from 0.75% (cerebellum) to 2.7% (Limbic) within subject, against 7.3%
(cerebellum) to 15.6% (SalVentAttn) between subjects. *Caveat:* DorsAttn
holds 2 regions, Cont 3 and cerebellum 2, so their ranks in the stability
order are fragile.
