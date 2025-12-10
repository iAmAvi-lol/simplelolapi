import requests
import os
import tkinter as tk
import threading
import time
import webbrowser

from dotenv import load_dotenv
from tkinter import ttk, messagebox, Menu

load_dotenv()

# TODO Get longer lasting API key
api_key = os.getenv("API_KEY")

api_get_puuid = (
    "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
)
api_get_matchhistory = (
    "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/"
)
api_get_matchdata = "https://americas.api.riotgames.com/lol/match/v5/matches/"
api_get_rank = "https://na1.api.riotgames.com/lol/league/v4/entries/by-puuid/"
api_account_by_puuid = (
    "https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/"
)

app_version = "v0.0.1"

if not api_key:
    # We don't exit here so the GUI can show a helpful message, but most calls will fail.
    print(
        "Warning: API_KEY not found in environment. Set API_KEY or provide a .env file."
    )

# Module-level username/tagline variables (set by the GUI)
username = ""
tagline = ""


class APIManager:
    def __init__(self):
        self.puuid_data = None
        self.match_data = None
        self.specific_match = None
        self.rank_data = None

    def fetch_puuid(self):
        global username, tagline
        if not username or not tagline:
            raise RuntimeError("Username and tagline not set. Use the GUI to set them.")

        url = f"{api_get_puuid}{username}/{tagline}?api_key={api_key}"
        print("Fetching User PUUID:", url)
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        puuid = data.get("puuid")
        if not puuid:
            raise RuntimeError("PUUID not found in response.")
        self.puuid_data = puuid
        print("Stored user PUUID")
        return self.puuid_data

    def fetch_matches(self):
        if not self.puuid_data:
            raise RuntimeError("puuid_data not set. Call fetch_puuid first.")
        print("Fetching matches from API")
        response = requests.get(
            f"{api_get_matchhistory}{self.puuid_data}/ids?start=0&count=20&api_key={api_key}"
        )
        response.raise_for_status()
        self.match_data = response.json()
        print(f"Stored {len(self.match_data)} matches")
        return self.match_data

    def fetch_rank_data(self):
        if not self.puuid_data:
            raise RuntimeError("puuid_data not set. Call fetch_puuid first.")

        url = f"{api_get_rank}{self.puuid_data}?api_key={api_key}"
        response = requests.get(url)

        if response.status_code != 200:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            print(f"Rank endpoint returned status {response.status_code}: {payload}")
            self.rank_data = "Rank: Unknown"
            return self.rank_data

        data = response.json()

        if not data:
            self.rank_data = "Rank: Unranked"
            return self.rank_data

        entry = None
        for e in data:
            if e.get("queueType") == "RANKED_SOLO_5x5":
                entry = e
                break
        if entry is None:
            entry = data[0]

        tier = entry.get("tier")
        rank = entry.get("rank", "")
        lp = entry.get("leaguePoints", 0)

        if tier is None:
            print("Unexpected rank entry shape:", entry)
            self.rank_data = "Rank: Unknown"
            return self.rank_data

        self.rank_data = f"Rank:{tier} {rank} LP:{lp}"
        return self.rank_data

    def fetch_match_data(self, query_string):
        print("Loading Search Function")
        response = requests.get(f"{api_get_matchdata}{query_string}?api_key={api_key}")
        response.raise_for_status()
        self.specific_match = response.json()["metadata"]["participants"].index(
            self.puuid_data
        )
        response2 = response.json()["info"]["participants"][self.specific_match]
        print("\n" + "=" * 50)
        print("--- Loading Match Info ---")
        print("-" * 50)
        print(f"{username}#{tagline}")
        print(f"Champion Name: {response2['championName']}")
        print(f"Victory?: {response2['win']}")
        print(f"KDA: {response2['kills']}/{response2['deaths']}/{response2['assists']}")
        print(f"Vision Score: {response2['visionScore']}")
        print(f"Gold Earned: {response2['goldEarned']}")
        print(f"Damage Dealt: {response2['totalDamageDealtToChampions']}")
        return self.specific_match

    def detaied_details(self):
        """Get match data with participants"""
        print("📊 Fetching match data...")
        url = f"{api_get_matchdata}{self.specific_match}?api_key={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error getting match data: {response.status_code}")
            return None

    def clear_data(self):
        self.puuid_data = None
        self.match_data = None
        self.specific_match = None
        self.rank_data = None
        print("All data cleared from memory")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Riot Viewer")
        self.root.geometry("820x720")
        self.api_manager = None
        self.output_visible = False
        self.create_menu_bar()
        self._build_ui()

    def create_menu_bar(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # file
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)

        # settings
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Clear Data", command=self.clear_cache)

        # help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Source", command=self.open_documentation)

    def clear_cache(self):
        if messagebox.askyesno(
            "Clear Data", "Are you sure you want to clear all cached data?"
        ):
            if self.api_manager:
                self.api_manager.clear_data()
            self.on_clear()

    def show_about(self):
        about_text = f"Simple League Tool {app_version}"
        messagebox.showinfo("About", about_text)

    def open_documentation(self):
        webbrowser.open("https://github.com/iAmAvi-lol/simplelolapi")

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text='Enter "Username#TAG":').grid(row=0, column=0, sticky="w")
        self.user_tag_entry = ttk.Entry(top, width=44)
        self.user_tag_entry.grid(row=0, column=1, padx=(6, 12), sticky="w")

        self.fetch_btn = ttk.Button(top, text="GO!", command=self.on_fetch_user)
        self.fetch_btn.grid(row=0, column=2, padx=(6, 6))

        self.clear_btn = ttk.Button(top, text="Clear", command=self.on_clear)
        self.clear_btn.grid(row=0, column=3, padx=(6, 0))

        self.status_label = ttk.Label(frm, text="Ready", relief="sunken", anchor="w")
        self.status_label.pack(fill="x", pady=(4, 8))

        main = ttk.Frame(frm)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 8))

        ttk.Label(left, text="Matches:").pack(anchor="w")
        self.match_listbox = tk.Listbox(left, width=40, height=20)
        self.match_listbox.pack(side="left", fill="y")
        self.match_listbox.bind("<Double-Button-1>", self.on_show_selected_match)

        scrollbar = ttk.Scrollbar(
            left, orient="vertical", command=self.match_listbox.yview
        )
        scrollbar.pack(side="left", fill="y")
        self.match_listbox.config(yscrollcommand=scrollbar.set)

        left_buttons = ttk.Frame(left)
        left_buttons.pack(fill="x", pady=(6, 0))
        self.show_btn = ttk.Button(
            left_buttons, text="Show Match", command=self.on_show_selected_match
        )
        self.show_btn.pack(side="left")
        self.refresh_btn = ttk.Button(
            left_buttons, text="Refresh", command=self.on_refresh_matches
        )
        self.refresh_btn.pack(side="left", padx=(6, 0))

        self.analyze_btn = ttk.Button(
            left_buttons, text="Analyze Match", command=self.on_analyze_selected_match
        )
        self.analyze_btn.pack(side="left", padx=(6, 0))

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(right, text="Details:").pack(anchor="w")
        self.details_text = tk.Text(right, wrap="word", state="disabled")
        self.details_text.pack(fill="both", expand=True)

        self.output_frame = ttk.Frame(frm)
        ttk.Label(self.output_frame, text="Analysis Output:").pack(anchor="w")
        self.output_text = tk.Text(
            self.output_frame, wrap="word", height=12, state="disabled"
        )
        self.output_text.pack(fill="both", expand=True)

    # --- UI helpers ---

    def set_status(self, msg: str):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def set_details(self, text: str):
        def _set():
            self.details_text.config(state="normal")
            self.details_text.delete("1.0", "end")
            self.details_text.insert("1.0", text)
            self.details_text.config(state="disabled")

        self.root.after(0, _set)

    def append_details(self, text: str):
        def _append():
            self.details_text.config(state="normal")
            self.details_text.insert("end", text + "\n")
            self.details_text.see("end")
            self.details_text.config(state="disabled")

        self.root.after(0, _append)

    def set_output_text(self, text: str):
        def _set():
            # Ensure output frame is visible
            if not self.output_visible:
                self.output_frame.pack(fill="both", expand=False, pady=(8, 0))
                self.output_visible = True
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", text)
            self.output_text.config(state="disabled")

        self.root.after(0, _set)

    def append_output(self, text: str):
        def _append():
            if not self.output_visible:
                self.output_frame.pack(fill="both", expand=False, pady=(8, 0))
                self.output_visible = True
            self.output_text.config(state="normal")
            self.output_text.insert("end", text + "\n")
            self.output_text.see("end")
            self.output_text.config(state="disabled")

        self.root.after(0, _append)

    def populate_matches(self, matches):
        def _populate():
            self.match_listbox.delete(0, "end")
            for m in matches:
                self.match_listbox.insert("end", m)

        self.root.after(0, _populate)

    def enable_controls(self, enable: bool = True):
        def _set():
            state = "normal" if enable else "disabled"
            self.fetch_btn.config(state=state)
            self.clear_btn.config(state=state)
            self.show_btn.config(state=state)
            self.refresh_btn.config(state=state)
            self.analyze_btn.config(state=state)
            e_state = "normal" if enable else "disabled"
            self.user_tag_entry.config(state=e_state)

        self.root.after(0, _set)

    def _get_puuid(self):
        if not self.api_manager:
            return None
        return getattr(self.api_manager, "puuid", None) or getattr(
            self.api_manager, "puuid_data", None
        )

    # --- Actions ---

    def on_clear(self):
        self.user_tag_entry.delete(0, "end")
        self.match_listbox.delete(0, "end")
        self.set_details("")
        self.set_status("Cleared")
        self.api_manager = None
        # clear module-level username/tagline
        global username, tagline
        username = ""
        tagline = ""
        # hide output
        if self.output_visible:
            self.output_frame.pack_forget()
            self.output_visible = False
            self.set_output_text("")

    def _parse_user_tag(self, raw: str):
        if not raw:
            return None, None
        parts = raw.rsplit("#", 1)
        if len(parts) != 2:
            return None, None
        u, t = parts[0].strip(), parts[1].strip()
        if not u or not t:
            return None, None
        return u, t

    def on_fetch_user(self):
        raw = self.user_tag_entry.get().strip()
        u, t = self._parse_user_tag(raw)
        if not u:
            messagebox.showwarning(
                "Input required", 'Please enter the user as "Username#Tagline".'
            )
            return

        if not api_key:
            messagebox.showerror(
                "Missing API Key",
                "API_KEY not set in environment. Put it in .env or export it.",
            )
            return

        # set module-level username/tagline for APIManager
        global username, tagline
        username = u
        tagline = t

        try:
            manager = APIManager()
        except Exception as e:
            messagebox.showerror(
                "APIManager Error", f"Could not create APIManager: {e}"
            )
            return

        # assign the manager and start background fetch
        self.api_manager = manager
        self.enable_controls(False)
        self.set_status("Loading user data...")
        t_worker = threading.Thread(target=self._worker_fetch_user, daemon=True)
        t_worker.start()

    def _worker_fetch_user(self):
        if not self.api_manager:
            self.set_details("Internal error: API not available.")
            self.set_status("Error")
            self.enable_controls(True)
            return

        try:
            puuid = self.api_manager.fetch_puuid()
            self.set_status("Fetched PUUID, fetching rank...")
            rank = self.api_manager.fetch_rank_data()
            self.set_status("Fetched rank, fetching matches...")
            matches = self.api_manager.fetch_matches()
            puuid_val = self._get_puuid() or puuid
            self.set_details(
                f"User: {username}#{tagline}\nPUUID: {puuid_val}\nRank: {rank}\n\nMatches: {len(matches)}"
            )
            self.populate_matches(matches)
            self.set_status("Ready")
        except Exception as e:
            self.set_details(f"Error: {e}")
            self.set_status("Error")
        finally:
            self.enable_controls(True)

    def on_refresh_matches(self):
        if not self.api_manager or not self._get_puuid():
            messagebox.showinfo("No user", "Enter a username")
            return
        t_worker = threading.Thread(target=self._worker_refresh_matches, daemon=True)
        self.enable_controls(False)
        self.set_status("Refreshing matches...")
        t_worker.start()

    def _worker_refresh_matches(self):
        if not self.api_manager:
            self.append_details("Internal error: API manager not available.")
            self.set_status("Error")
            self.enable_controls(True)
            return
        try:
            matches = self.api_manager.fetch_matches()
            self.populate_matches(matches)
            self.set_status("Matches refreshed")
        except Exception as e:
            self.append_details(f"Error refreshing matches: {e}")
            self.set_status("Error")
        finally:
            self.enable_controls(True)

    def on_show_selected_match(self, event=None):
        sel = self.match_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select a match", "Please select a match from the list")
            return
        idx = sel[0]
        match_id = self.match_listbox.get(idx)
        t_worker = threading.Thread(
            target=self._worker_show_match, args=(match_id,), daemon=True
        )
        self.enable_controls(False)
        self.set_status(f"Loading match {match_id}...")
        t_worker.start()

    def _worker_show_match(self, match_id: str):
        if not self.api_manager:
            self.append_details("Internal error: API manager not available.")
            self.set_status("Error")
            self.enable_controls(True)
            return

        try:
            puuid_val = self._get_puuid()
            if not puuid_val:
                raise RuntimeError("PUUID not available for the selected user.")

            resp = requests.get(
                f"{api_get_matchdata}{match_id}?api_key={api_key}", timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            participants = data.get("metadata", {}).get("participants", [])
            try:
                idx = participants.index(puuid_val)
            except ValueError:
                raise RuntimeError(
                    "This user's puuid is not in the selected match's participants."
                )

            my_part = data.get("info", {}).get("participants", [])[idx]

            pretty = []
            pretty.append("=" * 60)
            pretty.append(f"Match ID: {match_id}")
            pretty.append(f"Player: {username}#{tagline}")
            pretty.append(f"Champion: {my_part.get('championName')}")
            pretty.append(f"Victory: {my_part.get('win')}")
            pretty.append(
                f"K/D/A: {my_part.get('kills')}/{my_part.get('deaths')}/{my_part.get('assists')}"
            )
            pretty.append(f"Vision Score: {my_part.get('visionScore')}")
            pretty.append(f"Gold Earned: {my_part.get('goldEarned')}")
            pretty.append(f"Damage Dealt: {my_part.get('totalDamageDealtToChampions')}")
            pretty.append("=" * 60)
            self.append_details("\n".join(pretty))
            self.set_status("Match loaded")
        except Exception as e:
            self.append_details(f"Error loading match: {e}")
            self.set_status("Error")
        finally:
            self.enable_controls(True)

    def on_analyze_selected_match(self):
        sel = self.match_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select a match", "Please select a match from the list")
            return
        idx = sel[0]
        match_id = self.match_listbox.get(idx)
        # ensure output window is visible
        if not self.output_visible:
            self.output_frame.pack(fill="both", expand=False, pady=(8, 0))
            self.output_visible = True
        self.set_output_text(f"Analyzing match {match_id}...\n")
        t_worker = threading.Thread(
            target=self._worker_analyze_match, args=(match_id,), daemon=True
        )
        self.enable_controls(False)
        self.set_status(f"Analyzing match {match_id}...")
        t_worker.start()

    def _worker_analyze_match(self, match_id: str):
        try:
            # 1) Fetch match data
            resp = requests.get(
                f"{api_get_matchdata}{match_id}?api_key={api_key}", timeout=20
            )
            resp.raise_for_status()
            match_data = resp.json()

            participants = match_data.get("info", {}).get("participants", [])
            puuids = [p.get("puuid") for p in participants if p.get("puuid")]
            if not puuids:
                self.append_output("No participants found in this match.")
                self.set_status("Error")
                return

            # 2) Map puuids -> Riot IDs (gameName#tagLine)
            summoner_names = {}
            for i, puuid in enumerate(puuids):
                try:
                    time.sleep(0.1)  # small rate limiting
                    url = f"{api_account_by_puuid}{puuid}?api_key={api_key}"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        game_name = d.get("gameName", "Unknown")
                        tag_line = d.get("tagLine", "")
                        summoner_names[puuid] = (
                            f"{game_name}#{tag_line}" if tag_line else game_name
                        )
                    else:
                        summoner_names[puuid] = f"Error {r.status_code}"
                except Exception:
                    summoner_names[puuid] = "Error"

            # 3) Get ranked info per puuid
            ranked_info = {}
            headers = {"X-Riot-Token": api_key}
            for i, puuid in enumerate(puuids):
                try:
                    time.sleep(0.2)  # rate limiting
                    url = f"{api_get_rank}{puuid}"
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        entries = r.json()
                        if isinstance(entries, list) and len(entries) > 0:
                            solo_queue = None
                            for entry in entries:
                                if entry.get("queueType") == "RANKED_SOLO_5x5":
                                    solo_queue = entry
                                    break
                            if solo_queue:
                                tier = solo_queue.get("tier", "UNRANKED").title()
                                rank = solo_queue.get("rank", "")
                                lp = solo_queue.get("leaguePoints", 0)
                                wins = solo_queue.get("wins", 0)
                                losses = solo_queue.get("losses", 0)
                                ranked_info[puuid] = {
                                    "tier": tier,
                                    "rank": rank,
                                    "lp": lp,
                                    "wins": wins,
                                    "losses": losses,
                                    "full_rank": f"{tier} {rank} ({lp} LP)"
                                    if rank
                                    else f"{tier} ({lp} LP)",
                                }
                            else:
                                ranked_info[puuid] = {"full_rank": "Unranked"}
                        else:
                            ranked_info[puuid] = {"full_rank": "Unranked"}
                    else:
                        ranked_info[puuid] = {"full_rank": f"Error {r.status_code}"}
                except Exception:
                    ranked_info[puuid] = {"full_rank": "Error"}

            # 4) Calculate team stats (blue team teamId==100, red==200)
            def calculate_team_stats(team_participants):
                total_kills = 0
                total_deaths = 0
                total_assists = 0
                rank_values = []

                tier_values = {
                    "IRON": 1,
                    "BRONZE": 2,
                    "SILVER": 3,
                    "GOLD": 4,
                    "PLATINUM": 5,
                    "EMERALD": 6,
                    "DIAMOND": 7,
                    "MASTER": 8,
                    "GRANDMASTER": 9,
                    "CHALLENGER": 10,
                }

                for p in team_participants:
                    puuid = p.get("puuid")
                    total_kills += p.get("kills", 0)
                    total_deaths += p.get("deaths", 0)
                    total_assists += p.get("assists", 0)

                    rank_data = ranked_info.get(puuid, {})
                    if "tier" in rank_data:
                        rank_values.append(
                            tier_values.get(rank_data["tier"].upper(), 0)
                        )

                avg_rank = sum(rank_values) / len(rank_values) if rank_values else 0
                avg_kda = (total_kills + total_assists) / max(total_deaths, 1)

                return {
                    "kills": total_kills,
                    "deaths": total_deaths,
                    "assists": total_assists,
                    "avg_kda": avg_kda,
                    "avg_rank": avg_rank,
                }

            blue_team = [p for p in participants if p.get("teamId") == 100]
            red_team = [p for p in participants if p.get("teamId") == 200]

            blue_stats = calculate_team_stats(blue_team)
            red_stats = calculate_team_stats(red_team)

            out_lines = []
            queue_id = match_data.get("info", {}).get("queueId", 0)
            queue_names = {
                420: "Ranked Solo/Duo",
                440: "Ranked Flex",
                400: "Normal Draft",
                430: "Normal Blind",
                450: "ARAM",
            }
            queue_name = queue_names.get(queue_id, f"Queue {queue_id}")

            out_lines.append("\n" + "=" * 90)
            out_lines.append(f"MATCH ANALYSIS - {queue_name}")
            out_lines.append("=" * 90 + "\n")

            out_lines.append("🔵 BLUE TEAM:")
            out_lines.append("-" * 90)
            out_lines.append(
                f"{'Player':<25} {'Champion':<15} {'K/D/A':<12} {'Rank':<20} {'CS':<6} {'Gold':<8}"
            )
            out_lines.append("-" * 90)

            for p in blue_team:
                puuid = p.get("puuid")
                summoner_name = summoner_names.get(puuid, "Unknown")
                champion = p.get("championName", "Unknown")
                kills = p.get("kills", 0)
                deaths = p.get("deaths", 0)
                assists = p.get("assists", 0)
                cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
                gold = p.get("goldEarned", 0)

                rank_data = ranked_info.get(puuid, {})
                rank_display = rank_data.get("full_rank", "Unranked")

                out_lines.append(
                    f"{summoner_name:<25} {champion:<15} {f'{kills}/{deaths}/{assists}':<12} {rank_display:<20} {cs:<6} {gold:,}<8"
                )

            out_lines.append(
                f"\n📊 Blue Team Stats: Kills: {blue_stats['kills']} | Deaths: {blue_stats['deaths']} | Assists: {blue_stats['assists']} | Avg KDA: {blue_stats['avg_kda']:.2f}\n"
            )

            out_lines.append("🔴 RED TEAM:")
            out_lines.append("-" * 90)
            out_lines.append(
                f"{'Player':<25} {'Champion':<15} {'K/D/A':<12} {'Rank':<20} {'CS':<6} {'Gold':<8}"
            )
            out_lines.append("-" * 90)

            for p in red_team:
                puuid = p.get("puuid")
                summoner_name = summoner_names.get(puuid, "Unknown")
                champion = p.get("championName", "Unknown")
                kills = p.get("kills", 0)
                deaths = p.get("deaths", 0)
                assists = p.get("assists", 0)
                cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
                gold = p.get("goldEarned", 0)

                rank_data = ranked_info.get(puuid, {})
                rank_display = rank_data.get("full_rank", "Unranked")

                out_lines.append(
                    f"{summoner_name:<25} {champion:<15} {f'{kills}/{deaths}/{assists}':<12} {rank_display:<20} {cs:<6} {gold:,}<8"
                )

            out_lines.append(
                f"\n📊 Red Team Stats: Kills: {red_stats['kills']} | Deaths: {red_stats['deaths']} | Assists: {red_stats['assists']} | Avg KDA: {red_stats['avg_kda']:.2f}\n"
            )

            # Team comparison
            out_lines.append("=" * 90)
            out_lines.append("TEAM COMPARISON")
            out_lines.append("-" * 90)

            tier_names = [
                "Iron",
                "Bronze",
                "Silver",
                "Gold",
                "Platinum",
                "Emerald",
                "Diamond",
                "Master",
                "Grandmaster",
                "Challenger",
            ]
            blue_avg_tier = (
                tier_names[int(blue_stats["avg_rank"]) - 1]
                if 1 <= blue_stats["avg_rank"] <= 10
                else "Unknown"
            )
            red_avg_tier = (
                tier_names[int(red_stats["avg_rank"]) - 1]
                if 1 <= red_stats["avg_rank"] <= 10
                else "Unknown"
            )

            out_lines.append(
                f"🔵 Blue Team Avg Rank: ~{blue_avg_tier} ({blue_stats['avg_rank']:.1f})"
            )
            out_lines.append(
                f"🔴 Red Team Avg Rank: ~{red_avg_tier} ({red_stats['avg_rank']:.1f})"
            )
            advantage_rank = (
                "Blue"
                if blue_stats["avg_rank"] > red_stats["avg_rank"]
                else "Red"
                if red_stats["avg_rank"] > blue_stats["avg_rank"]
                else "Even"
            )
            advantage_kills = (
                "Blue"
                if blue_stats["kills"] > red_stats["kills"]
                else "Red"
                if red_stats["kills"] > blue_stats["kills"]
                else "Even"
            )
            out_lines.append(f"📈 Rank Advantage: {advantage_rank}")
            out_lines.append(f"⚔️  Kill Advantage: {advantage_kills}")

            # Determine which team won (use first participant of one team)
            winning_team = "Blue" if blue_team and blue_team[0].get("win") else "Red"
            out_lines.append(f"🏆 Winning Team: {winning_team}")

            out_lines.append("\n" + "=" * 90)

            final_output = "\n".join(out_lines)
            self.set_output_text(final_output)
            self.set_status("Analysis complete")
        except Exception as e:
            self.append_output(f"Error analyzing match: {e}")
            self.set_status("Error")
        finally:
            self.enable_controls(True)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
