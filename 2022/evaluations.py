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
from string import ascii_uppercase
import textwrap

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import utils


import_dir = "G:/My Drive/IASD/CE Committee/2022/Presentation Evaluations/Qualtrics Data"
import_name = "IASD+CE+Evaluation+and+Attendance+Survey+2022_September+11,+2022_14.29.sav"
import_path = Path(import_dir) / import_name

session_path = Path("./hidden-sessions2022.json")
participant_path = Path("./hidden-participants2022.json")

# export_dir = "G:/My Drive/IASD/CE Materials/2022/Presentation Evaluations/Results"
export_dir = Path("C:/Users/malle/Desktop/IASDCE")
export_dir.mkdir(exist_ok=True)

########################################################
# Load data
########################################################

likert_columns = [
    "Learning",
    "Communication",
    "Attentive",
    "Useful",
    "Sensitive",
    "Recommend",
    "LearningObjectives_1",
    "LearningObjectives_2",
    "LearningObjectives_3",
]


df, meta = utils.load_spss(import_path)
df = utils.cleanse(df, spam_ok=True)
# df = utils.validate_likert_scales(meta, likert_columns)


float2str_map = meta.variable_value_labels["PresentationID"]
df["PresentationTitle"] = df["PresentationID"].map(float2str_map)

letters = [l for l in ascii_uppercase] + ["AA"]
lettermap = {v: letters[i] for i, v in enumerate(float2str_map.values())}
df["PresentationCode"] = df["PresentationTitle"].map(lettermap)




########## FOR EACH PRESENTATION
## Group comments together
comments = df.groupby("PresentationCode")["Comments"].agg(lambda x: ":::".join(x))


# Group likert scales

# df["PresentationID"] = pd.Categorical(df["PresentationID"])
summary = df.groupby("PresentationCode")[likert_columns].describe()

# melted = pd.melt(df,
#     id_vars=["PresentationCode"],
#     value_vars=likert_columns,
#     var_name="Question",
#     value_name="Response",
# )

cmap = sns.color_palette("rocket")

# fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
# sns.countplot(
#     x=df["PresentationCode"],
#     order=letters,
#     palette=cmap,
# )
# ax.set_ylabel("Number of responses")
# ax.set_xlabel("Presentation Code")
# export_path = export_dir / f"samplesizes.png"
# plt.savefig(export_path, dpi=300)
# plt.close()

for col in likert_columns:
    fig, (ax, ax2) = plt.subplots(ncols=2,
        figsize=(6, 6), constrained_layout=True,
        gridspec_kw={"width_ratios": [3, 1]},
        sharey=True, sharex=False)

    ser = df[["PresentationCode", "Learning"]].dropna()["PresentationCode"]

    sns.countplot(
        y=df["PresentationCode"],
        order=letters,
        palette=cmap,
        orient="h",
        ax=ax2,
    )
    ax2.set_ylabel(None)
    ax2.set_yticks([])
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_xlabel("Number\nof Responses")

    sns.boxplot(data=df,
        x=col,
        y="PresentationCode",
        order=letters,
        # color="blue",
        # orient="h",
        width=0.7,
        palette=cmap,
        whis=[0, 100],
        linewidth=1,
        saturation=1,
        ax=ax
    )
    question_str = meta.column_names_to_labels[col]
    question_str = textwrap.fill(question_str, width=60)

    qfloats, qstrings = zip(*meta.variable_value_labels[col].items())

    fig.suptitle(question_str)
    ax.set_xticks(qfloats)
    ax.set_xlabel("Response Options")
    ax.set_ylabel("Presentation Code")
    ax.set_xticklabels(qstrings, rotation=25, ha="right")
    ax.spines["left"].set_position(("outward", 5))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim((qfloats[0]-0.1, qfloats[-1]+0.1))

    export_path = export_dir / f"summary-{col}.png"

    plt.savefig(export_path, dpi=300)
    plt.close()
