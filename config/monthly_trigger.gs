/**
 * Google Apps Script — Monthly Delta Scrape Trigger
 * 
 * HOW TO INSTALL:
 * 1. Open your Google Spreadsheet
 * 2. Extensions → Apps Script
 * 3. Paste this entire file into the editor
 * 4. Replace WEBHOOK_URL with your actual endpoint (see options below)
 * 5. Run setupMonthlyTrigger() once manually to register the schedule
 * 6. Done — it will fire on the 1st of every month at 8am
 *
 * WEBHOOK OPTIONS (pick one):
 *
 * Option A — Make.com (easiest, no server needed):
 *   - Create a Make.com scenario with a Webhook trigger
 *   - Add an HTTP module that POSTs to your machine running the agents
 *   - Or use Make's "Run a script" module if you host on a cloud VM
 *
 * Option B — Direct HTTP to a cloud server:
 *   - Deploy agent2_delta_scrape.py on a small VM (Railway, Render, Fly.io)
 *   - Expose a POST /run-delta endpoint
 *   - Paste that URL below
 *
 * Option C — Run locally (manual trigger via this script):
 *   - Set WEBHOOK_URL to a free service like webhook.site to test
 *   - Then manually run the agents on your machine when notified
 */

var WEBHOOK_URL = "https://YOUR_WEBHOOK_OR_SERVER_URL_HERE";

// ── Main trigger function ─────────────────────────────────────────

function runMonthlyScrape() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet();
  var statSheet = sheet.getSheetByName("system_state") 
                  || sheet.insertSheet("system_state");

  Logger.log("Monthly delta scrape trigger fired: " + new Date().toISOString());

  try {
    var response = UrlFetchApp.fetch(WEBHOOK_URL, {
      method: "POST",
      contentType: "application/json",
      payload: JSON.stringify({
        trigger: "monthly_delta_scrape",
        fired_at: new Date().toISOString(),
        spreadsheet_id: sheet.getId(),
      }),
      muteHttpExceptions: true,
    });

    var status = response.getResponseCode();
    Logger.log("Webhook response: " + status);

    // Log the trigger in the state sheet
    _logTrigger(statSheet, status === 200 ? "SUCCESS" : "FAILED (" + status + ")");

  } catch (e) {
    Logger.log("Trigger error: " + e.toString());
    _logTrigger(statSheet, "ERROR: " + e.toString());
  }
}

// ── Set up the monthly schedule ───────────────────────────────────

function setupMonthlyTrigger() {
  // Delete any existing triggers for this function to avoid duplicates
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "runMonthlyScrape") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  // Create new monthly trigger — fires on the 1st of each month at 8am
  ScriptApp.newTrigger("runMonthlyScrape")
    .timeBased()
    .onMonthDay(1)
    .atHour(8)
    .create();

  Logger.log("Monthly trigger set: fires on the 1st of each month at 8am");
}

// ── Remove the trigger ────────────────────────────────────────────

function removeTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "runMonthlyScrape") {
      ScriptApp.deleteTrigger(triggers[i]);
      Logger.log("Trigger removed.");
    }
  }
}

// ── Test the webhook manually ─────────────────────────────────────

function testWebhook() {
  Logger.log("Testing webhook...");
  runMonthlyScrape();
}

// ── Internal: log trigger runs to state sheet ─────────────────────

function _logTrigger(statSheet, result) {
  var lastRow = statSheet.getLastRow();
  if (lastRow === 0) {
    statSheet.appendRow(["key", "value", "updated_at"]);
  }

  // Find or update the trigger_last_run row
  var data = statSheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] === "trigger_last_run") {
      statSheet.getRange(i + 1, 2).setValue(result);
      statSheet.getRange(i + 1, 3).setValue(new Date().toISOString());
      return;
    }
  }
  // Not found — append
  statSheet.appendRow(["trigger_last_run", result, new Date().toISOString()]);
}
