import numpy as np
import pyreadstat

def load_spss(filepath):
    """Returns dataframe and metadata object."""
    df, meta = pyreadstat.read_sav(filepath)
    return df, meta

def validate_likert_scales(meta, vars_to_validate):
    """Sometimes when the Qualtrics question is edited
    the scale gets changed "unknowingly". Here, check
    to make sure everything starts at 1 and increases by 1.
    Could be remapped but it's easier and safer to fix
    the source of the problem in Qualtrics.
    """
    msgs = []
    for var in vars_to_validate:
        if var in meta.variable_value_labels:
            levels = meta.variable_value_labels[var]
            values = list(levels.keys())
            if values[0] != 1:
                msgs.append(f"{var} scale doesn't start at 1. Recode values in Qualtrics and re-export.")
            if values != sorted(values):
                msgs.append(f"{var} scale is not in increasing order. Recode values in Qualtrics and re-export.")
            if np.any(np.diff(values) != 1):
                msgs.append(f"{var} scale is not linear. Recode values in Qualtrics and re-export.")
    assert not msgs, "\n".join(msgs)

def cleanse(df, spam_ok=False, keep_columns=[]):
    """The qualtrics file comes baked with some columns we don't need.
    Make sure they are all "in order" or as expected,
    and then take them off the dataframe.
    Nothing is specific to this study here.

    Spam might be okay, for example with CE stuff.

    Removes non-anonymous links (pilot participants)
    and those who didn't finish (actually not sure about the latter).
    
    https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/data/download-data/understanding-your-dataset/
    """

    # Exclude any submissions prior to the original study advertisement.
    # Convert to the Qualtrics timestamps from MST to CST since that's the time I have it in.
    for col in ["StartDate", "EndDate", "RecordedDate"]:
        df[col] = df[col].dt.tz_localize("US/Mountain").dt.tz_convert("US/Central")

    # Sort for readability
    df = df.sort_values("StartDate")

    ################################# Handle Qualtrics-specific columns.
    ## These have nothing to do with out data.
    ## Check all the Qualtrics columns and make sure they look as expected.
    ## Then remove them for cleanliness.

    ##### Remove piloting/testing data.
    # That should handle all the "previews" from this column, but check.
    df = df.query("DistributionChannel=='anonymous'")
    # assert df["DistributionChannel"].eq("anonymous").all(), "All surveys should have come from the anonymous link."
    # This is also redundnat but make sure "IP Address" is here (just indicates normal response, IP was not collected).
    # df = df.query("Status=='IP Address'")
    # assert df["Status"].eq("IP Address").all(), "All surveys should have come from the anonymous link."
    acceptable_statuses = [0]
    if spam_ok:
        acceptable_statuses.append(8)
    ## !! these response keys are also in <meta>
    ## !! so could actually print them out or check more explicitly.
    assert df["Status"].isin(acceptable_statuses).all(), "Found >= 1 unacceptable Status."

    ##### Remove unfinished surveys.
    ##### (This only catches those that left early,
    #####  if they just skipped some non-required Qs they will stay.)
    # "Finished" is binary, True if they didn't manually exit (ie, True even if screedn out early).
    # "Progress" is percentage of completion, even if screened out, so a more useful measure.
    # BUT I think bc I screened w/ branching rather than skipping, they all say 100% even if they get screened out.
    # So this can be handled another way. Some questions were
    # required so check for this. The last question was required,
    # so use that as the measure of completion.
    # Still make sure Finished and Progress are both full (as I'm expecting)
    # I think there's a way to export with incomplete I probably didn't check that.
    # Or they might be "in progress"?
    df = df.query("Finished==1")
    df = df.query("Progress==100") # redundant I think

    # Can't see how these would be off but w/e just check
    assert df["ResponseId"].is_unique, "These should all be unique."
    assert df["UserLanguage"].eq("EN").all(), "All languages should be English."

    ## Description of Qualtrics default columns
    ## https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/data/download-data/understanding-your-dataset/

    ################################# Handle Qualtrics-specific columns.
    ## These have nothing to do with out data.
    ## Check all the Qualtrics columns and make sure they look as expected.
    ## Then remove them for cleanliness.

    # Remove default Qualtrics columns
    drop_columns = [
        "StartDate", "EndDate", "RecordedDate",         # Qualtrics stuff we're done with.
        "Status", "DistributionChannel", "Progress",    # Qualtrics stuff we're done with.
        "Finished", "ResponseId", "UserLanguage",       # Qualtrics stuff we're done with.
        "Duration__in_seconds_",
    ]
    for c in keep_columns:
        drop_columns.remove(c)

    df = df.drop(columns=drop_columns)
    return df
