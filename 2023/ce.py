"""
"""
from pathlib import Path
import pandas as pd
import pyreadstat

parent = Path("~").expanduser() / "Desktop"
import_name = "IASD+CE+Evaluation+and+Attendance+Survey+2023_August+12,+2023_14.44.sav"
import_path = parent / import_name
export_path = parent / "credits.csv"
import_path2 = parent / "CE Registration List 6-14-2023.csv"

df, meta = pyreadstat.read_sav(import_path)

df["ParticipantEmail"] = df["ParticipantEmail"].str.lower()
df = df[df["ParticipantEmail"].ne("me@you.com")]
df = df[df["ParticipantEmail"].ne("me@m.com")]
df["ParticipantEmail"] = df["ParticipantEmail"].replace(
    {"vergvennett@gmail.com": "vergebennett@gmail.com"}
)

data = (df
    .astype({"ParticipantEmail": "category", "AttendanceCode": "category"})
    .groupby("ParticipantEmail")
    ["AttendanceCode"].value_counts(dropna=False)
    .rename("Tally")
    .reset_index()
)




# Make sure there are no unexplained >1 values.
# Nobody should've filled out form more than once for the same presentation.
# # Binarize credits
data["Attended"] = data["Tally"].gt(0)
data = data[data["Attended"]]


# Make sure there are no unexplained 999999 Attendance Codes.
# Those were only for test purposes.
data = data[data["AttendanceCode"].ne("999999")].reset_index(drop=True)

# Add how much each presentation was worth.
data["Credits"] = data["AttendanceCode"].map(
    {
        "498732": 2,
        "613908": 1,
        "245601": 2,
        "759834": 1.5,
        "126587": 2,
        "392046": 2,
        "874910": 1.5,
    }
)

# Calculate total credits per person.
results = data.groupby("ParticipantEmail")["Credits"].sum()

# Add full names to make it easier to input manually for certificates.
names = pd.read_csv(import_path2, index_col="Email").rename_axis("ParticipantEmail")
names.index = names.index.str.lower()

results_with_names = names.join(results, how="outer")
results_with_names["Credits"] = results_with_names["Credits"].fillna(0)


# Export.
results_with_names.to_csv(export_path, na_rep="n/a")
