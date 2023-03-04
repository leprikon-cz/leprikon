import axios from 'axios';
import { LeprikonApi } from "./generated/api";
import { Configuration } from "./generated/configuration";


const apiUrlMetaTag = document.head.querySelector(`meta[name="leprikon-api-url"]`);
const basePath = apiUrlMetaTag && apiUrlMetaTag.getAttribute("content") || window.origin;
const configuration = new Configuration({
    baseOptions: { withCredentials: true },
    basePath,
});
axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

const api = new LeprikonApi(configuration);

export default api;
