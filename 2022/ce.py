"""Aggregate raw output from CE evaluations (Tucson, 2022).

Output a (n_participants, n_presentations) matrix indicating whether
the participant is missing anything. Group the presentations by session.

1. Load/clean raw Qualtrics output.
2. 
compare_surveys_and_signatures:
    To make sure that each participant completed a survey
    for all their signed-off talks (and vice-versa).

evaluate_attendance:
    Visualize how many people attended, which sessions, which types, etc.

evaluate_sessions:
    Visualize how well participants liked the program overall
    and for individual sessions.

annual_report:
    Generate the APA annual report.
    This might need the descriptions of talks etc.

1. Load and clean raw Qualtrics survey output.
2. Make sure that 
-> Then can send out Certificates after these:
    - Need their final survey data (including education level).
    - If not, just send a new survey, and say I'll reply with the certificate,
        which could be the future way.

Other script/functions.
1. Load data.
2. Plot descriptives
"""
from pathlib import Path
import sys; sys.path.append("C:/Users/malle/packages/dmlab")
import dmlab

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import_dir = "G:/My Drive/IASD/CE Materials/2022/Presentation Evaluations/Qualtrics Data"
import_name = "IASD+CE+Evaluation+and+Attendance+Survey+2022_September+11,+2022_14.29.sav"
import_path = Path(import_dir) / import_name

session_path = Path("./hidden-sessions2022.json")
participant_path = Path("./hidden-participants2022.json")

export_dir = "G:/My Drive/IASD/CE Materials/2022/Presentation Evaluations/Results"
export_path_totals = Path(export_dir) / "totals_awarded.csv"
export_path_heatmap = Path(export_dir) / "participantXpresentation.png"
export_path_totals.parent.mkdir(exist_ok=True)

########################################################
# Load data
########################################################

df, meta = dmlab.qualtrics.load_spss(import_path)
df = dmlab.qualtrics.standard_cleanse(df, spam_ok=True)
# df = dmlab.qualtrics.validate_likert_scales(meta, df.columns)

session_key = dmlab.io.load_json(session_path)
participant_key = dmlab.io.load_json(participant_path)

# Convert participant ID to full string identifier.
assert df["ParticipantID"].notna().all()
assert df["ParticipantID"].apply(float.is_integer).all()
df["ParticipantID"] = df["ParticipantID"].map(lambda x: f"pid-{x:03.0f}")

# Add a presenter's name column.
df["PresentationName"] = df["PresentationID"].map(meta.variable_value_labels["PresentationID"])
df["PresenterLastName"] = df["PresentationName"].str.split(",").str[0]
assert df["PresenterLastName"].notna().all()

# Generate an index of all presentations.
all_presentations = []
for k, v in session_key.items():
    for pres in v["presenters"]:
        all_presentations.append((k, pres))
index_of_presentations = pd.MultiIndex.from_tuples(all_presentations, names=["session_id", "presenter_name"])

# Generate an index of all participants.
all_participants = list(participant_key)
index_of_participants = pd.Index(all_participants, name="participant_id")

# Generate empty dataframe to fill.
res = pd.DataFrame(columns=index_of_participants, index=index_of_presentations)

# Make sure there were no new participants or presentations in Qualtrics.
assert df["PresenterLastName"].isin(res.index.get_level_values("presenter_name").unique()).all()
assert df["ParticipantID"].isin(res.columns).all()

# Make a dict that holds presenters evaluated by each participant.
evaluations_key = df.groupby("ParticipantID")["PresenterLastName"].apply(list).to_dict()

# For every participant/presentation combo, find out if they are:
#   Green - Signed off and evaluated
#   Yellow - Signed off but not evaluated
#   Red - Evaluated but not signed off
#   White - Neither evaluated nor signed off

for pid in index_of_participants:

    # Get the presentations they evaluated and sessions they got signed off.
    sessions_signed_off = participant_key[pid]["sessions_signed"] if "sessions_signed" in participant_key[pid] else []
    sessions_signed_off = [ f"ses-{x:03d}" for x in sessions_signed_off ]
    presentations_evaluated = evaluations_key[pid] if pid in evaluations_key else []

    for presentation in index_of_presentations:
        session_id, presenter_name = presentation
        signed = session_id in sessions_signed_off
        evaluated = presenter_name in presentations_evaluated
        if signed and evaluated:
            score = 3
        elif signed and not evaluated:
            score = 2
        elif evaluated and not signed:
            score = 1
        else:
            assert not signed and not evaluated
            continue
        res.loc[presentation, pid] = score


res = res.astype(float)


# Get credits awarded per participant

sess = pd.DataFrame.from_dict(session_key, orient="index").rename_axis("session_id")
# Convert presentation length to amount of CE credits.
sess["credits"] = sess["length"].div(60)

# Require a 1 in just 1 or more presentation of each session
credited = res.groupby("session_id").max().ge(1).astype(float)

totals = credited.mul(sess["credits"], axis=0).sum(axis=0).rename("n_credits")

totals.to_csv(export_path_totals)

# Plot

sns.set_style("white")
cmap = ["red", "yellow", "green"]

ax = sns.heatmap(res.T,
    cmap=["red", "yellow", "green"],
    cbar_kws={"ticks": [1.33, 2, 2.66]},
    linewidths=.5, linecolor="black",
    square=True, annot=False,
)

fig = plt.gcf()
cbar_ax = fig.axes[-1]
cbar_ax.set_yticklabels([
    "Evaluated but\nno signature",
    "Signed but\nno evaluation",
    "Signed and evaluated",
])

ax.set_ylabel("Participant ID")
ax.set_xlabel("Session ID and Presenter Name")

plt.tight_layout()

plt.savefig(export_path_heatmap, dpi=300)
plt.close()

# # Load manually-entered files about participant signoff sheets and session info.
# session_key = dmlab.io.load_json(session_path)
# participant_key = dmlab.io.load_json(participant_path)
# ses_df = pd.DataFrame.from_dict(session_key, orient="index").rename_axis("session_id")
# sub_df = pd.DataFrame.from_dict(participant_key, orient="index").rename_axis("subject_id")
# ses_df.index = ses_df.index.astype(int)
# sub_df.index = sub_df.index.astype(int)

# # Convert presentation length to amount of CE credits.
# ses_df["credits"] = ses_df["length"].div(60)


# # Generate empty dataframe to fill.
# all_subjects = set(map(int, participant_key)) | set(df["ParticipantID"])
# index = pd.Index(all_subjects, name="subject_id")
# columns = ["signed_up", "submitted_signatures"]

# ########################################################
# # Checks
# ########################################################

# # Grab a list of everyone who signed up for CE.
# all_subjects = list(participant_key)
# # Grab a list of everyone who completed the signoff form.
# signed_subjects = [ k for k, v in participant_key.items() if "sessions_attended" in v ]
# # Grab a list of everyone who completed a Qualtrics survey.
# survey_subjects = df["ParticipantID"].unique().tolist()

# # Reduce to unique values and match datatypes.
# all_subjects = set( int(x) for x in sorted(all_subjects) )
# signed_subjects = set( int(x) for x in sorted(signed_subjects) )
# survey_subjects = set( int(x) for x in sorted(survey_subjects) )

# # Make sure these are the same.
# did_nothing_subjects = all_subjects - (signed_subjects | survey_subjects)
# signed_only_subjects = signed_subjects - survey_subjects
# survey_only_subjects = survey_subjects - signed_subjects
# if did_nothing_subjects:
#     print("These participants signed up for CE but didn't turn in a signed form or complete any Qualtrics surveys:", *did_nothing_subjects)
# if signed_only_subjects:
#     print("These participants turned in a signed sheet but didn't do any Qualtrics forms:", *signed_only_subjects)
# if survey_only_subjects:
#     print("These participants turned in Qualtrics survey(s) but didn't turn in a signed sheet:", *survey_only_subjects)

# # Remove participants that fail.
# bad_subjects = did_nothing_subjects | survey_only_subjects | signed_only_subjects
# df = df[~df["ParticipantID"].isin(bad_subjects)]

# # Check that participants filled out all the surveys they needed to.
# for subject_id, subject_df in df.groupby("ParticipantID"):

#     # Grab the sessions this person got signed off for.
#     signed_sessions = sub_df.loc[subject_id, "sessions_attended"]

#     # Grab all the individual presentations within those sessions.
#     signed_presenters = set(ses_df.loc[signed_sessions, "presenters"].explode())

#     if not subject_df["PresenterLastName"].is_unique:
#         print("Subject", subject_id, "did multiple surveys for the same talk??")
#         print(subject_df["PresenterLastName"].value_counts())
#     surveyed_presenters = set(subject_df["PresenterLastName"])
#     surveyed_only = surveyed_presenters - signed_presenters
#     signed_only = signed_presenters - surveyed_presenters
#     if surveyed_only:
#         print("Subject", subject_id, "did a survey for", surveyed_only, "and did not get them signed.")
#     if signed_only:
#         print("Subject", subject_id, "got a signature for", signed_only, "and did not do the survey.")
#     # assert subject_df["PresenterLastName"].size == len(signed_presenters)
#     # assert subject_df["PresenterLastName"].isin(signed_presenters).all()

#     # # Check that each participant completed surveys for each
#     # # presentation they got signed off on, and no more.
#     # presenters_signed_off = participant_legend[participant_id]["attended_presentations"]
#     # presenters_surveyed = participant_df["PresenterLastName"].tolist()
#     # presenters_signed_off = sorted(presenters_signed_off)
#     # presenters_surveyed = sorted(presenters_surveyed)
#     # for presenter in presenters_signed_off:
#     #     if presenter not in presenters_surveyed:
#     #         print(f"Participant {participant_id} got signed off for {presenter}'s talk but did not complete a form for them.")
#     # for presenter in presenters_surveyed:
#     #     if presenter not in presenters_signed_off:
#     #         print(f"Participant {participant_id} got completed a form for {presenter}'s talk but did not get a signature.")

