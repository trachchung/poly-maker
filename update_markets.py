import os
import time
import traceback
from datetime import datetime

import pandas as pd  # Data analysis library
from gspread_dataframe import set_with_dataframe  # Library for updating Google Sheets

from data_updater.find_markets import (
    add_volatility_to_df,
    get_all_markets,
    get_all_results,
    get_markets,
    get_sel_df,
)
from data_updater.google_utils import get_spreadsheet
from data_updater.trading_utils import get_clob_client

# Configuration: Toggle Google Sheets saving
SAVE_TO_SHEETS = False  # Set to False to only save CSV files

# Initialize global variables
# spreadsheet = get_spreadsheet()
client = get_clob_client()

# wk_all = spreadsheet.worksheet("All Markets")
# wk_vol = spreadsheet.worksheet("Volatility Markets")

# sel_df = get_sel_df(spreadsheet, "Selected Markets")


def save_to_csv(data, filename_prefix, timestamp=None):
    """
    Save DataFrame to CSV file with timestamp

    Args:
        data: pandas DataFrame to save
        filename_prefix: prefix for the filename
        timestamp: optional timestamp, defaults to current time
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create data directory if it doesn't exist
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(CURRENT_DIR, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    filename = f"{data_dir}/{filename_prefix}_{timestamp}.csv"

    try:
        data.to_csv(filename, index=False)
        print(f"Saved {filename_prefix} data to {filename} ({len(data)} rows)")
    except Exception as e:
        print(f"Error saving {filename_prefix} to CSV: {str(e)}")


def update_sheet(data, worksheet):
    all_values = worksheet.get_all_values()
    existing_num_rows = len(all_values)
    existing_num_cols = len(all_values[0]) if all_values else 0

    num_rows, num_cols = data.shape
    max_rows = max(num_rows, existing_num_rows)
    max_cols = max(num_cols, existing_num_cols)

    # Create a DataFrame with the maximum size and fill it with empty strings
    padded_data = pd.DataFrame("", index=range(max_rows), columns=range(max_cols))

    # Update the padded DataFrame with the original data and its columns
    padded_data.iloc[:num_rows, :num_cols] = data.values
    padded_data.columns = list(data.columns) + [""] * (max_cols - num_cols)

    # Update the sheet with the padded DataFrame, including column headers
    set_with_dataframe(
        worksheet,
        padded_data,
        include_index=False,
        include_column_header=True,
        resize=True,
    )


def sort_df(df):
    # Calculate the mean and standard deviation for each column
    mean_gm = df["gm_reward_per_100"].mean()
    std_gm = df["gm_reward_per_100"].std()

    mean_volatility = df["volatility_sum"].mean()
    std_volatility = df["volatility_sum"].std()

    # Standardize the columns
    df["std_gm_reward_per_100"] = (df["gm_reward_per_100"] - mean_gm) / std_gm
    df["std_volatility_sum"] = (df["volatility_sum"] - mean_volatility) / std_volatility

    # Define a custom scoring function for best_bid and best_ask
    def proximity_score(value):
        if 0.1 <= value <= 0.25:
            return (0.25 - value) / 0.15
        elif 0.75 <= value <= 0.9:
            return (value - 0.75) / 0.15
        else:
            return 0

    df["bid_score"] = df["best_bid"].apply(proximity_score)
    df["ask_score"] = df["best_ask"].apply(proximity_score)

    # Create a composite score (higher is better for rewards, lower is better for volatility, with proximity scores)
    df["composite_score"] = (
        df["std_gm_reward_per_100"]
        - df["std_volatility_sum"]
        + df["bid_score"]
        + df["ask_score"]
    )

    # Sort by the composite score in descending order
    sorted_df = df.sort_values(by="composite_score", ascending=False)

    # Drop the intermediate columns used for calculation
    sorted_df = sorted_df.drop(
        columns=[
            "std_gm_reward_per_100",
            "std_volatility_sum",
            "bid_score",
            "ask_score",
            "composite_score",
        ]
    )

    return sorted_df


def fetch_and_process_data():
    global spreadsheet, client, wk_all, wk_vol, sel_df

    # spreadsheet = get_spreadsheet()
    # client = get_clob_client()

    # wk_all = spreadsheet.worksheet("All Markets")
    # wk_vol = spreadsheet.worksheet("Volatility Markets")
    # wk_full = spreadsheet.worksheet("Full Markets")

    # sel_df = get_sel_df(spreadsheet, "Selected Markets")

    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    all_df = get_all_markets(client)
    print("Got all Markets")

    # Save raw markets data to CSV
    save_to_csv(all_df, "all_markets_raw", timestamp)

    all_results = get_all_results(all_df, client)
    print("Got all Results")

    # Save orderbook results to CSV
    all_results_df = pd.DataFrame(all_results)
    save_to_csv(all_results_df, "all_results_orderbook", timestamp)

    m_data, all_markets = get_markets(all_results, sel_df, maker_reward=0.75)
    print("Got all orderbook")

    # Save processed markets data to CSV
    save_to_csv(m_data, "processed_markets", timestamp)

    print(
        f'{pd.to_datetime("now")}: Fetched all markets data of length {len(all_markets)}.'
    )
    new_df = add_volatility_to_df(all_markets)
    new_df["volatility_sum"] = new_df["24_hour"] + new_df["7_day"] + new_df["14_day"]

    new_df = new_df.sort_values("volatility_sum", ascending=True)
    new_df["volatilty/reward"] = (
        (new_df["gm_reward_per_100"] / new_df["volatility_sum"]).round(2)
    ).astype(str)

    new_df = new_df[
        [
            "question",
            "answer1",
            "answer2",
            "spread",
            "rewards_daily_rate",
            "gm_reward_per_100",
            "sm_reward_per_100",
            "bid_reward_per_100",
            "ask_reward_per_100",
            "volatility_sum",
            "volatilty/reward",
            "min_size",
            "1_hour",
            "3_hour",
            "6_hour",
            "12_hour",
            "24_hour",
            "7_day",
            "30_day",
            "best_bid",
            "best_ask",
            "volatility_price",
            "max_spread",
            "tick_size",
            "neg_risk",
            "market_slug",
            "token1",
            "token2",
            "condition_id",
        ]
    ]

    volatility_df = new_df.copy()
    volatility_df = volatility_df[new_df["volatility_sum"] < 20]
    # volatility_df = sort_df(volatility_df)
    volatility_df = volatility_df.sort_values("gm_reward_per_100", ascending=False)

    new_df = new_df.sort_values("gm_reward_per_100", ascending=False)

    # Save final processed data to CSV
    save_to_csv(new_df, "final_processed_markets", timestamp)
    save_to_csv(volatility_df, "low_volatility_markets", timestamp)

    print(f'{pd.to_datetime("now")}: Fetched select market of length {len(new_df)}.')

    if len(new_df) > 50:
        if SAVE_TO_SHEETS:
            print(f'{pd.to_datetime("now")}: Updating Google Sheets...')
            update_sheet(new_df, wk_all)
            update_sheet(volatility_df, wk_vol)
            update_sheet(m_data, wk_full)
            print(f'{pd.to_datetime("now")}: Google Sheets updated successfully.')
        else:
            print(
                f'{pd.to_datetime("now")}: Skipping Google Sheets update (SAVE_TO_SHEETS=False).'
            )
    else:
        print(
            f'{pd.to_datetime("now")}: Not updating sheet because of length {len(new_df)}.'
        )


if __name__ == "__main__":
    while True:
        try:
            fetch_and_process_data()
            time.sleep(60 * 60)  # Sleep for an hour
        except Exception as e:
            traceback.print_exc()
            print(str(e))
