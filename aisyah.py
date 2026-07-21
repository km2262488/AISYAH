#!/usr/bin/env python3
"""
AISYAH - Website Load Tester with Live Dashboard
Real-time monitoring with rich terminal UI 
"""

import time
import statistics
import threading
from datetime import datetime
from collections import deque, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from queue import Queue, Empty

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box
from rich.text import Text

# Try to import optional plotting library
try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False

console = Console()

# ============================================================================
# AISYAH Banner - Compact
# ============================================================================

AISYAH_BANNER = """
╔═══════════════════════════════════════════╗
 █████╗ ██╗███████╗██╗   ██╗ █████╗ ██╗  ██╗
██╔══██╗██║██╔════╝╚██╗ ██╔╝██╔══██╗██║  ██║
███████║██║███████╗ ╚████╔╝ ███████║███████║
██╔══██║██║╚════██║  ╚██╔╝  ██╔══██║██╔══██║
██║  ██║██║███████║   ██║   ██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
╚═══════════════════════════════════════════╝
"""

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class AisyahRequestResult:
    """Single request result"""
    request_id: int
    status_code: Optional[int]
    response_time: Optional[float]
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class AisyahStats:
    """Real-time statistics with safe calculations"""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    status_codes: Counter = field(default_factory=Counter)
    errors: List[Dict] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful / self.total_requests) * 100
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def requests_per_second(self) -> float:
        if self.elapsed_time == 0:
            return 0.0
        return self.total_requests / self.elapsed_time
    
    @property
    def min_response_time(self) -> Optional[float]:
        return min(self.response_times) if self.response_times else None
    
    @property
    def max_response_time(self) -> Optional[float]:
        return max(self.response_times) if self.response_times else None
    
    @property
    def avg_response_time(self) -> Optional[float]:
        if not self.response_times:
            return None
        try:
            return statistics.mean(self.response_times)
        except statistics.StatisticsError:
            return None
    
    @property
    def median_response_time(self) -> Optional[float]:
        if not self.response_times:
            return None
        try:
            return statistics.median(self.response_times)
        except statistics.StatisticsError:
            return None
    
    def get_percentile(self, percentile: int) -> Optional[float]:
        """Get percentile value safely"""
        if not self.response_times or len(self.response_times) < 2:
            return None
        try:
            sorted_times = sorted(self.response_times)
            idx = min(int(len(sorted_times) * percentile / 100), len(sorted_times) - 1)
            return sorted_times[idx]
        except (IndexError, ValueError):
            return None

# ============================================================================
# AISYAH Live Dashboard - Separate Boxes
# ============================================================================

class AisyahDashboard:
    """Aisyah Live dashboard """
    
    def __init__(self):
        self.stats = AisyahStats()
        self.running = False
        self.live = None
        self._history = deque(maxlen=60)
        self._bar_data = []
        
        # Color schemes
        self.colors = {
            'success': 'green',
            'failed': 'red',
            'warning': 'yellow',
            'info': 'blue',
            'highlight': 'cyan'
        }
        
    def update(self, result: AisyahRequestResult):
        """Update statistics with new result"""
        self.stats.total_requests += 1
        
        if result.success:
            self.stats.successful += 1
            if result.response_time is not None:
                self.stats.response_times.append(result.response_time)
                self._history.append({
                    'timestamp': result.timestamp,
                    'response_time': result.response_time,
                    'status': 'success'
                })
                self._bar_data.append(result.response_time)
                if len(self._bar_data) > 30:
                    self._bar_data.pop(0)
        else:
            self.stats.failed += 1
            if result.error:
                self.stats.errors.append({
                    'id': result.request_id,
                    'error': result.error
                })
                self._history.append({
                    'timestamp': result.timestamp,
                    'response_time': 0,
                    'status': 'error'
                })
                self._bar_data.append(0)
                if len(self._bar_data) > 30:
                    self._bar_data.pop(0)
        
        if result.status_code:
            self.stats.status_codes[result.status_code] += 1
            
        self.stats.last_update = time.time()
    
    def get_status_color(self) -> str:
        """Get color based on success rate"""
        rate = self.stats.success_rate
        if rate >= 95:
            return self.colors['success']
        elif rate >= 80:
            return self.colors['warning']
        else:
            return self.colors['failed']
    
    def create_summary_panel(self) -> Panel:
        """Create summary statistics panel - Separate"""
        try:
            table = Table.grid(padding=(0, 1))
            table.add_column(justify="right", style="bold", width=10)
            table.add_column(width=20)
            
            status_color = self.get_status_color()
            elapsed = self.stats.elapsed_time
            
            table.add_row("Status", f"[{status_color}]● {'RUNNING' if self.running else 'STOP'}[/]")
            table.add_row("Duration", self._format_time(elapsed))
            table.add_row("Requests", f"{self.stats.total_requests:,}")
            table.add_row("✅ OK", f"[green]{self.stats.successful:,}[/]")
            table.add_row("❌ Fail", f"[red]{self.stats.failed:,}[/]")
            table.add_row("Rate", f"[{status_color}]{self.stats.success_rate:.1f}%[/]")
            table.add_row("RPS", f"{self.stats.requests_per_second:.1f}")
            
            return Panel(
                table,
                title="📊 SUMMARY",
                border_style=status_color,
                box=box.ROUNDED
            )
        except Exception as e:
            return Panel(f"Error", title="SUMMARY", border_style="red")
    
    def create_stats_panel(self) -> Panel:
        """Create statistics panel - Separate"""
        try:
            table = Table.grid(padding=(0, 1))
            table.add_column(justify="right", style="bold", width=10)
            table.add_column(width=20)
            
            # Response time stats
            table.add_row("Avg", self._format_ms_safe(self.stats.avg_response_time))
            table.add_row("Med", self._format_ms_safe(self.stats.median_response_time))
            table.add_row("Min", self._format_ms_safe(self.stats.min_response_time, color="green"))
            table.add_row("Max", self._format_ms_safe(self.stats.max_response_time, color="red"))
            
            # Percentiles
            p95 = self.stats.get_percentile(95)
            p99 = self.stats.get_percentile(99)
            
            if p95 is not None:
                table.add_row("P95", f"{p95:.0f}ms")
            if p99 is not None:
                table.add_row("P99", f"[yellow]{p99:.0f}ms[/]")
            
            return Panel(
                table,
                title="⚡ PERFORMANCE",
                border_style="yellow",
                box=box.ROUNDED
            )
        except Exception as e:
            return Panel(f"Error", title="PERFORMANCE", border_style="red")
    
    def create_status_codes_panel(self) -> Panel:
        """Create status codes distribution panel - Separate"""
        try:
            if not self.stats.status_codes:
                return Panel("No data yet", title="📋 STATUS CODES", border_style="blue")
            
            table = Table.grid(padding=(0, 1))
            table.add_column(justify="right", style="bold", width=8)
            table.add_column(width=22)
            
            # Sort by count descending
            sorted_codes = sorted(self.stats.status_codes.items(), key=lambda x: x[1], reverse=True)
            
            for code, count in sorted_codes[:5]:  # Show top 5 status codes
                color = "green" if code == 200 else "yellow" if code < 400 else "red"
                pct = (count / self.stats.total_requests) * 100 if self.stats.total_requests > 0 else 0
                table.add_row(f"HTTP {code}", f"[{color}]{count:,} ({pct:.1f}%)[/]")
            
            return Panel(
                table,
                title="📋 STATUS CODES",
                border_style="blue",
                box=box.ROUNDED
            )
        except Exception as e:
            return Panel(f"Error", title="STATUS CODES", border_style="red")
    
    def create_errors_panel(self) -> Panel:
        """Create errors summary panel - Separate"""
        try:
            if not self.stats.errors:
                return Panel("✅ No errors detected", title="⚠ ERRORS", border_style="green")
            
            error_table = Table.grid(padding=(0, 1))
            error_table.add_column(justify="right", style="bold", width=8)
            error_table.add_column(width=22)
            
            error_counts = Counter(e['error'] for e in self.stats.errors[-10:])
            for error, count in error_counts.most_common(2):
                error_table.add_row(f"#{count}", f"[red]{error[:30]}...[/]")
            
            total_errors = len(self.stats.errors)
            if total_errors > 2:
                error_table.add_row("Total", f"[red]{total_errors}[/]")
            
            return Panel(
                error_table,
                title=f"⚠ ERRORS ({len(self.stats.errors)})",
                border_style="red",
                box=box.ROUNDED
            )
        except Exception as e:
            return Panel(f"Error", title="ERRORS", border_style="red")
    
    def create_bar_chart_plotext(self) -> Panel:
        """Create bar chart using plotext"""
        try:
            if not HAS_PLOTEXT or len(self._bar_data) < 2:
                return Panel(
                    "📊 Install plotext for charts",
                    title="📊 BAR CHART",
                    border_style="cyan"
                )
            
            data = self._bar_data[-30:]
            if len(data) < 2:
                return Panel("Insufficient data", title="📊 BAR CHART", border_style="cyan")
            
            plt.clf()
            plt.bar(range(len(data)), data, color='cyan', width=0.8)
            plt.title(f"Last {len(data)} requests")
            plt.xlabel("Request")
            plt.ylabel("Time (ms)")
            plt.theme("dark")
            
            # Add average line
            if self.stats.avg_response_time:
                plt.axhline(y=self.stats.avg_response_time, color='yellow', linestyle='--', label='Avg')
            
            plot_str = plt.build()
            
            return Panel(
                plot_str,
                title="📊 BAR CHART",
                border_style="cyan",
                box=box.ROUNDED
            )
        except Exception as e:
            return self.create_ascii_bar_chart()
    
    def create_ascii_bar_chart(self) -> Panel:
        """Create simple ASCII bar chart without plotext"""
        try:
            if not self._bar_data or len(self._bar_data) < 2:
                return Panel(
                    "📊 Waiting for data...",
                    title="📊 BAR CHART",
                    border_style="cyan"
                )
            
            data = list(self._bar_data)[-20:]
            max_val = max(data) if data else 1
            
            bars = []
            for i, val in enumerate(data):
                if val > 0:
                    width = int((val / max_val) * 25)
                    color = "green" if val < 200 else "yellow" if val < 500 else "red"
                    bar = "█" * width
                    bars.append(f"{i+1:2d} │ [{color}]{bar:<25}[/] {val:.0f}ms")
                else:
                    bars.append(f"{i+1:2d} │ [red]✗[/]")
            
            bar_text = "\n".join(bars[-15:])
            
            # Add average line if available
            avg_text = ""
            if self.stats.avg_response_time:
                avg_text = f"\n── Avg: {self.stats.avg_response_time:.0f}ms ──"
            
            return Panel(
                f"{bar_text}{avg_text}",
                title="📊 BAR CHART",
                border_style="cyan",
                box=box.ROUNDED
            )
        except Exception as e:
            return Panel(f"Error: {e}", title="BAR CHART", border_style="red")
    
    def create_dashboard(self) -> Layout:
        """Create the full dashboard layout - Separate Boxes"""
        try:
            # Create main layout with padding for separation
            layout = Layout()
            layout.split(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            # Header with AISYAH branding
            header_text = Text()
            header_text.append("🌸 AISYAH ", style="bold magenta")
            header_text.append("LIVE DASHBOARD", style="bold white")
            header_text.append(f"  {datetime.now().strftime('%H:%M:%S')}", style="dim")
            layout["header"].update(Panel(Align.center(header_text), border_style="magenta"))
            
            # Body - Vertical layout with each panel as separate box
            body = Layout()
            body.split(
                Layout(name="summary", size=9),
                Layout(name="stats", size=8),
                Layout(name="status", size=7),
                Layout(name="history", size=10),
                Layout(name="errors", size=6)
            )
            
            # Each panel is a separate box with spacing
            body["summary"].update(self.create_summary_panel())
            body["stats"].update(self.create_stats_panel())
            body["status"].update(self.create_status_codes_panel())
            body["history"].update(self.create_ascii_bar_chart())
            body["errors"].update(self.create_errors_panel())
            
            layout["body"].update(body)
            
            # Footer
            footer_text = Text()
            footer_text.append("🌸 AISYAH", style="magenta")
            footer_text.append(" • ", style="dim")
            footer_text.append("Ctrl+C", style="bold white")
            footer_text.append(" to stop", style="dim")
            layout["footer"].update(Align.center(footer_text))
            
            return layout
        except Exception as e:
            layout = Layout()
            layout.split(Layout(name="error"))
            layout["error"].update(Panel(f"Error: {e}", title="Error", border_style="red"))
            return layout
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration"""
        try:
            if seconds < 60:
                return f"{seconds:.0f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        except:
            return "0s"
    
    def _format_ms_safe(self, value: Optional[float], color: str = None) -> str:
        """Format milliseconds"""
        try:
            if value is None:
                return "N/A"
            if value < 1000:
                result = f"{value:.0f}ms"
            else:
                result = f"{value/1000:.1f}s"
            
            if color:
                return f"[{color}]{result}[/]"
            return result
        except:
            return "N/A"
    
    def display(self):
        """Display the dashboard in live mode"""
        try:
            with Live(self.create_dashboard(), refresh_per_second=2, console=console) as live:
                self.live = live
                while self.running or self.stats.total_requests > 0:
                    try:
                        if self.live:
                            self.live.update(self.create_dashboard())
                        time.sleep(0.5)
                    except Exception as e:
                        console.print(f"[red]Update error: {e}[/]")
                        time.sleep(1)
        except Exception as e:
            console.print(f"[red]Display error: {e}[/]")

# ============================================================================
# AISYAH Website Load Tester
# ============================================================================

class AisyahLoadTester:
    """Main load tester class"""
    
    def __init__(self, url: str, num_requests: int = 100, num_threads: int = 10):
        self.url = url
        self.num_requests = num_requests
        self.num_threads = num_threads
        self.dashboard = AisyahDashboard()
        self.result_queue = Queue()
        self.running = False
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AISYAH-LoadTester/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        # Configure timeouts
        self.session.timeout = 30
        
    def make_request(self, request_id: int) -> AisyahRequestResult:
        """Make a single HTTP request"""
        try:
            start_time = time.time()
            response = self.session.get(self.url, timeout=30)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            
            return AisyahRequestResult(
                request_id=request_id,
                status_code=response.status_code,
                response_time=response_time,
                success=response.status_code == 200
            )
        except requests.exceptions.Timeout:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error="Timeout"
            )
        except requests.exceptions.ConnectionError:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error="Connection Error"
            )
        except Exception as e:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error=str(e)[:100]
            )
    
    def worker(self, request_ids: List[int]):
        """Worker thread to process requests"""
        for req_id in request_ids:
            if not self.running:
                break
            try:
                result = self.make_request(req_id)
                self.result_queue.put(result)
            except Exception as e:
                console.print(f"[red]Worker error: {e}[/]")
    
    def run_test(self) -> Dict[str, Any]:
        """Run the load test with dashboard"""
        try:
            console.clear()
            
            # Show AISYAH banner
            console.print(AISYAH_BANNER, style="magenta")
            console.print()
            
            # Show test info - Compact
            info_table = Table.grid(padding=(0, 1))
            info_table.add_column(justify="right", style="bold magenta", width=12)
            info_table.add_column(width=25)
            info_table.add_row("🌐 URL", self.url[:40])
            info_table.add_row("📊 Req", f"{self.num_requests:,}")
            info_table.add_row("⚡ Thr", str(self.num_threads))
            info_table.add_row("📅 Start", datetime.now().strftime('%H:%M:%S'))
            
            console.print(Panel(info_table, title="🌸 AISYAH CONFIG", 
                               border_style="magenta", box=box.ROUNDED))
            console.print()
            
            self.running = True
            self.dashboard.running = True
            
            # Start dashboard in separate thread
            dashboard_thread = threading.Thread(target=self.dashboard.display, daemon=True)
            dashboard_thread.start()
            
            # Process requests
            start_time = time.time()
            
            # Distribute requests among threads
            request_ids = list(range(self.num_requests))
            chunk_size = max(1, len(request_ids) // self.num_threads)
            chunks = [request_ids[i:i + chunk_size] for i in range(0, len(request_ids), chunk_size)]
            
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                # Submit work
                futures = []
                for chunk in chunks:
                    future = executor.submit(self.worker, chunk)
                    futures.append(future)
                
                # Process results as they come in
                completed = 0
                while completed < self.num_requests and self.running:
                    try:
                        result = self.result_queue.get(timeout=0.1)
                        self.dashboard.update(result)
                        completed += 1
                    except Empty:
                        continue
                
                # Wait for all futures to complete
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        console.print(f"[red]Future error: {e}[/]")
            
            self.running = False
            self.dashboard.running = False
            
            # Wait for dashboard to finish
            time.sleep(1)
            
            total_time = time.time() - start_time
            
            return self.generate_report(total_time)
            
        except Exception as e:
            console.print(f"[red]Test error: {e}[/]")
            return {}
    
    def generate_report(self, total_time: float) -> Dict[str, Any]:
        """Generate final report"""
        try:
            stats = self.dashboard.stats
            
            report = {
                'total_requests': stats.total_requests,
                'successful': stats.successful,
                'failed': stats.failed,
                'success_rate': stats.success_rate,
                'total_time': total_time,
                'rps': stats.total_requests / total_time if total_time > 0 else 0,
                'response_times': list(stats.response_times),
                'status_codes': dict(stats.status_codes),
                'errors': stats.errors
            }
            
            # Display final summary
            console.clear()
            console.print(Panel.fit(
                "[bold magenta]🌸 AISYAH - COMPLETED ✅[/]",
                border_style="magenta"
            ))
            console.print()
            
            # Summary Table
            summary_table = Table(box=box.ROUNDED, border_style="magenta")
            summary_table.add_column("Metric", style="bold magenta", width=12)
            summary_table.add_column("Value", justify="center", width=15)
            
            summary_table.add_row("Requests", f"{report['total_requests']:,}")
            summary_table.add_row("✅ OK", f"[green]{report['successful']:,}[/]")
            summary_table.add_row("❌ Fail", f"[red]{report['failed']:,}[/]")
            summary_table.add_row("Rate", f"{report['success_rate']:.1f}%")
            summary_table.add_row("Duration", f"{total_time:.1f}s")
            summary_table.add_row("RPS", f"{report['rps']:.1f}")
            
            if stats.avg_response_time is not None:
                summary_table.add_row("Avg", f"{stats.avg_response_time:.0f}ms")
            if stats.max_response_time is not None:
                summary_table.add_row("Max", f"[red]{stats.max_response_time:.0f}ms[/]")
            if stats.min_response_time is not None:
                summary_table.add_row("Min", f"[green]{stats.min_response_time:.0f}ms[/]")
            
            console.print(summary_table)
            console.print()
            
            # Status codes
            if report['status_codes']:
                status_table = Table(box=box.SQUARE, border_style="blue")
                status_table.add_column("Status", justify="center", style="bold", width=8)
                status_table.add_column("Count", justify="center", width=10)
                status_table.add_column("%", justify="center", width=6)
                
                for code, count in sorted(report['status_codes'].items()):
                    pct = (count / report['total_requests']) * 100 if report['total_requests'] > 0 else 0
                    color = "green" if code == 200 else "yellow" if code < 400 else "red"
                    status_table.add_row(str(code), f"[{color}]{count:,}[/]", f"{pct:.0f}%")
                
                console.print(status_table)
                console.print()
            
            # Summary
            console.print()
            if report['success_rate'] >= 95:
                console.print("[bold green]🎯 Excellent! Website is performing well.[/]")
            elif report['success_rate'] >= 80:
                console.print("[bold yellow]⚠️ Performance could be improved.[/]")
            else:
                console.print("[bold red]❌ Website may be experiencing issues.[/]")
            
            console.print()
            console.print("[dim]🌸 AISYAH - ALHAMDULILLAH [/]")
            
            return report
            
        except Exception as e:
            console.print(f"[red]Report error: {e}[/]")
            return {}

# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main entry point for AISYAH"""
    try:
        console.clear()
        
        # Show AISYAH Banner
        console.print(AISYAH_BANNER, style="magenta")
        console.print()
        console.print(Align.center("[dim]Load Tester with Live Dashboard by Aisyah[/]"))
        console.print()
        
        # Get user input
        url = console.input("[bold magenta]🌸 URL[/] [cyan]→[/] ").strip()
        
        if not url:
            console.print("[red]❌ URL cannot be empty![/]")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            num_requests_input = console.input("[bold magenta]📊 Req[/] [cyan]→[/] ").strip()
            num_requests = int(num_requests_input) if num_requests_input else 100
            
            num_threads_input = console.input("[bold magenta]⚡ Thr[/] [cyan]→[/] ").strip()
            num_threads = int(num_threads_input) if num_threads_input else 10
            
            # Validate
            num_requests = max(1, min(num_requests, 10000))
            num_threads = max(1, min(num_threads, 100))
            
        except ValueError:
            console.print("[red]⚠️ Invalid input! Using defaults.[/]")
            num_requests = 100
            num_threads = 10
        
        console.print()
        console.print("[dim]Press Ctrl+C to stop early.[/dim]")
        console.print()
        
        try:
            # Run test
            tester = AisyahLoadTester(url, num_requests, num_threads)
            results = tester.run_test()
            
        except KeyboardInterrupt:
            console.print("\n[bold magenta]🌸 AISYAH:[/] [yellow]⚠️ Interrupted.[/]")
            if hasattr(tester, 'running'):
                tester.running = False
                tester.dashboard.running = False
            console.print("[yellow]Generating partial report...[/yellow]")
            time.sleep(1)
            
    except KeyboardInterrupt:
        console.print("\n[bold magenta]🌸 AISYAH:[/] [yellow]Cancelled.[/]")
    except Exception as e:
        console.print(f"[bold magenta]🌸 AISYAH:[/] [red]Error: {e}[/]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
