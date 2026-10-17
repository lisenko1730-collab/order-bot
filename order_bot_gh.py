name: Order bot

on:
  schedule:
    - cron: "*/5 * * * *"
  workflow_dispatch:

concurrency:
  group: order-bot
  cancel-in-progress: false

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:
      - uses: actions/checkout@v4
      - name: Run bot
        run: python3 order_bot_gh.py
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          ADMIN_ID: ${{ secrets.ADMIN_ID }}
