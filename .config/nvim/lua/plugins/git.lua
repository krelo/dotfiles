return {
  {
    "NeogitOrg/neogit",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "sindrets/diffview.nvim",
      "nvim-telescope/telescope.nvim",
    },
    opts = {
      integrations = {
        diffview = true,
        telescope = true,
      },
      graph_style = "unicode",
    },
    keys = {
      { "<leader>gg", "<cmd>Neogit<cr>",        desc = "Open Neogit" },
      { "<leader>gc", "<cmd>Neogit commit<cr>", desc = "Git commit" },
      { "<leader>gp", "<cmd>Neogit push<cr>",   desc = "Git push" },
      { "<leader>gl", "<cmd>Neogit pull<cr>",   desc = "Git pull" },
    },
  },
  {
    "sindrets/diffview.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    keys = {
      { "<leader>gd", "<cmd>DiffviewOpen<cr>",            desc = "Open Diffview" },
      { "<leader>gh", "<cmd>DiffviewFileHistory<cr>",     desc = "File history (repo)" },
      { "<leader>gH", "<cmd>DiffviewFileHistory %<cr>",   desc = "File history (current)" },
      { "<leader>gx", "<cmd>DiffviewClose<cr>",           desc = "Close Diffview" },
    },
  },
}
