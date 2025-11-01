import { LitElement, html, css } from "lit";

class SolarControlCard extends LitElement {
    static get properties() {
        return {
            hass: { type: Object },
            config: { type: Object },
        };
    }

    constructor() {
        super();
        this.config = {};
    }

    static styles = css`
        ha-card {
            padding: 16px;
        }
        .row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }
    `;

    setConfig(config) {
        this.config = config;
    }

    render() {
        return html`
            <ha-card header="${this.config.title || "Solar Control"}">
                <div class="row">
                    <span>Enabled</span>
                    <ha-switch
                        .checked=${this.config.enabled}
                        @change=${this._toggleEnabled.bind(this)}
                    ></ha-switch>
                </div>
                <div class="row">
                    <span>Power Requirement (Wh)</span>
                    <ha-textfield
                        .value=${String(this.config.power || "")}
                        @input=${this._updatePower.bind(this)}
                        type="number"
                        placeholder="e.g. 500"
                    ></ha-textfield>
                </div>
            </ha-card>
        `;
    }

    _toggleEnabled(e) {
        this.config = {
            ...this.config,
            enabled: e.target.checked,
        };
        this._fireConfigChanged();
    }

    _updatePower(e) {
        this.config = {
            ...this.config,
            power: Number(e.target.value),
        };
        this._fireConfigChanged();
    }

    _fireConfigChanged() {
        const event = new CustomEvent("config-changed", {
            detail: { config: this.config },
        });
        this.dispatchEvent(event);
    }
}

customElements.define("solar-control-card", SolarControlCard);
