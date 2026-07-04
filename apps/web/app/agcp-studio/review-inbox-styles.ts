export const AGCP_REVIEW_INBOX_CSS = `
  .agcp-connected-content:has(.review-inbox-route) {
    overflow: hidden;
    padding: 0;
  }

  .review-inbox-route {
    background:
      linear-gradient(180deg, rgba(18, 24, 32, .96), rgba(8, 11, 18, .98)),
      var(--bg);
    color: var(--text);
    display: grid;
    grid-template-columns: 390px minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    height: 100%;
    min-height: 0;
    overflow: hidden;
    width: 100%;
  }

  .review-business-header {
    align-items: center;
    border-bottom: 1px solid rgba(150, 170, 190, .12);
    display: grid;
    gap: 12px;
    grid-column: 1 / -1;
    grid-template-columns: minmax(0, 1fr) auto;
    min-height: 76px;
    padding: 14px 18px;
  }

  .review-business-header nav {
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    font-size: 12px;
    gap: 8px;
    grid-column: 1 / -1;
  }

  .review-business-title {
    align-items: center;
    display: flex;
    gap: 10px;
    min-width: 0;
  }

  .review-business-title h1 {
    color: #eef3f8;
    font-size: 24px;
    line-height: 1.05;
    margin: 0;
    min-width: 0;
  }

  .review-refresh-action {
    background: rgba(255, 255, 255, .035);
    border: 1px solid rgba(150, 170, 190, .16);
    border-radius: 6px;
    color: #cbd5df;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    min-height: 32px;
    padding: 0 12px;
    justify-self: end;
  }

  .review-inbox-pane {
    border-right: 1px solid rgba(150, 170, 190, .12);
    display: flex;
    flex-direction: column;
    grid-column: 1;
    grid-row: 2;
    min-height: 0;
    overflow: hidden;
  }

  .review-detail-pane {
    display: flex;
    grid-column: 2;
    grid-row: 2;
    min-height: 0;
    min-width: 0;
    overflow: auto;
  }

  .review-inbox-footer {
    align-items: center;
    display: flex;
    justify-content: space-between;
    min-height: 34px;
    padding: 0 16px;
  }

  @media (max-width: 900px) {
    .shell:has(.review-inbox-route) .topbar {
      gap: 8px;
      padding: 0 12px;
    }

    .shell:has(.review-inbox-route) .topbar-search,
    .shell:has(.review-inbox-route) .topbar-actions,
    .shell:has(.review-inbox-route) .topbar-spacer {
      display: none;
    }

    .review-inbox-route {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto minmax(0, 1fr);
      height: auto;
      min-height: calc(100vh - var(--agcp-topbar-height));
      overflow: auto;
    }

    .review-inbox-pane,
    .review-detail-pane {
      grid-column: 1;
    }

    .review-inbox-pane {
      grid-row: 2;
      max-height: 44vh;
    }

    .review-detail-pane {
      grid-row: 3;
    }

    .review-inbox-footer {
      font-size: 12px;
      gap: 10px;
    }
  }
`;
